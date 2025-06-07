import selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup as BeautifulSoup
import time
import os
import requests
import urllib.parse
import re
import logging
from retrying import retry
import hashlib
from urllib.parse import urlparse
from datetime import datetime
import random
from webdriver_manager.chrome import ChromeDriverManager
import platform
import sys

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Log system information
logger.info("="*50)
logger.info("System Information:")
logger.info(f"Python Version: {sys.version}")
logger.info(f"Platform: {platform.platform()}")
logger.info(f"Architecture: {platform.architecture()}")
logger.info("="*50)

# Rate limiting configuration
RATE_LIMIT_DELAY = 2  # seconds between requests
MAX_RETRIES = 3
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
]

def verify_chromedriver():
    """Verify ChromeDriver installation and version"""
    try:
        chrome_driver_path = os.path.join(os.getcwd(), "chromedriver.exe")
        if not os.path.exists(chrome_driver_path):
            logger.error(f"ChromeDriver not found at: {chrome_driver_path}")
            return False
        
        # Check if it's a 64-bit executable
        import struct
        with open(chrome_driver_path, 'rb') as f:
            f.seek(0x3C)  # PE header offset
            pe_header_offset = struct.unpack('<I', f.read(4))[0]
            f.seek(pe_header_offset + 4)  # Machine type offset
            machine_type = struct.unpack('<H', f.read(2))[0]
            
        is_64bit = machine_type == 0x8664
        logger.info(f"ChromeDriver is {'64-bit' if is_64bit else '32-bit'}")
        
        if not is_64bit:
            logger.error("ChromeDriver must be 64-bit to match your Chrome installation")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error verifying ChromeDriver: {str(e)}")
        return False

def get_chrome_version():
    """Get the installed Chrome version"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        logger.info(f"Found Chrome version in registry: {version}")
        return version
    except Exception as e:
        logger.error(f"Error getting Chrome version from registry: {str(e)}")
        try:
            # Try alternative method using Chrome's path
            chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            if os.path.exists(chrome_path):
                import subprocess
                result = subprocess.run([chrome_path, '--version'], capture_output=True, text=True)
                version = result.stdout.strip().split()[-1]
                logger.info(f"Found Chrome version from executable: {version}")
                return version
        except Exception as e2:
            logger.error(f"Error getting Chrome version from executable: {str(e2)}")
        return None

def get_random_user_agent():
    """Get a random user agent from the list"""
    return random.choice(USER_AGENTS)

def rate_limit():
    """Add a random delay between requests to avoid rate limiting"""
    delay = RATE_LIMIT_DELAY + random.uniform(0, 1)
    time.sleep(delay)

def create_download_folder(base_folder="downloads"):
    """Create the download folder if it doesn't exist"""
    try:
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)
            logger.info(f"Created download folder: {base_folder}")
        return base_folder
    except Exception as e:
        logger.error(f"Error creating download folder: {str(e)}")
        raise

def get_absolute_url(base_url, href):
    """Convert relative URL to absolute URL"""
    try:
        if not href:
            return None
            
        if href.startswith('http'):
            return href
            
        # Handle relative URLs
        parsed_base = urlparse(base_url)
        if href.startswith('//'):
            return f"{parsed_base.scheme}:{href}"
        elif href.startswith('/'):
            return f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
        else:
            return urllib.parse.urljoin(base_url, href)
    except Exception as e:
        logger.error(f"Error getting absolute URL: {str(e)}")
        return None

def is_download_link(href):
    """Check if the link is a download link"""
    if not href:
        return False
    
    try:
        download_patterns = [
            r'download_file\.php',
            r'download\.php',
            r'get_file\.php',
            r'\.pdf$',
            r'/pdf/',
            r'download.*\.pdf',
            r'paper.*\.pdf',
            r'mark.*\.pdf'
        ]
        href_lower = href.lower()
        return any(re.search(pattern, href_lower) for pattern in download_patterns)
    except Exception as e:
        logger.error(f"Error checking download link: {str(e)}")
        return False

def get_filename_from_url(url, response):
    """Extract filename from URL or Content-Disposition header"""
    try:
        # Try to get filename from Content-Disposition header
        if 'Content-Disposition' in response.headers:
            cd = response.headers['Content-Disposition']
            if 'filename=' in cd:
                filename = re.findall("filename=(.+)", cd)[0]
                return filename.strip('"')
        
        # Try to get filename from URL
        parsed = urlparse(url)
        path = parsed.path
        query = parsed.query
        
        # If it's a PHP file, try to get the filename from query parameters
        if 'download_file.php' in path or 'download.php' in path:
            params = urllib.parse.parse_qs(query)
            if 'file' in params:
                return params['file'][0]
            if 'filename' in params:
                return params['filename'][0]
        
        # Fallback to path basename
        filename = os.path.basename(path)
        if not filename or filename == 'download_file.php':
            # Generate a filename based on the URL hash
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"paper_{url_hash}.pdf"
        
        # Clean filename
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        
        return filename
    except Exception as e:
        logger.error(f"Error getting filename: {str(e)}")
        return f"error_{hash(url)}.pdf"

@retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
def scrape_website(website):
    """Scrape website for PDF download links"""
    try:
        logger.info("="*50)
        logger.info(f"Starting scraping process for: {website}")
        logger.info("="*50)
        
        # Get Chrome version
        chrome_version = get_chrome_version()
        if not chrome_version:
            raise Exception("Could not determine Chrome version. Please ensure Chrome is installed.")
        logger.info(f"Detected Chrome version: {chrome_version}")
        
        # Verify ChromeDriver before starting
        if not verify_chromedriver():
            raise Exception("ChromeDriver verification failed. Please ensure you have the correct 64-bit version installed.")
        
        logger.info("Launching chrome browser...")
        download_folder = create_download_folder()

        options = webdriver.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # options.add_argument("--headless=new")  # Commented out for debugging
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(f"user-agent={get_random_user_agent()}")
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        options.add_argument("--disable-site-isolation-trials")
        
        # Add window size for visible mode
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        
        logger.info("Initializing Chrome driver...")
        try:
            # Use local ChromeDriver
            chrome_driver_path = os.path.join(os.getcwd(), "chromedriver.exe")
            if not os.path.exists(chrome_driver_path):
                raise Exception(f"ChromeDriver not found at: {chrome_driver_path}")
            
            service = ChromeService(executable_path=chrome_driver_path)
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_window_size(1920, 1080)
            logger.info("Chrome driver initialized successfully")
        except Exception as e:
            error_msg = str(e)
            if "This version of ChromeDriver only supports Chrome version" in error_msg:
                logger.error(f"ChromeDriver version mismatch. Your Chrome version is {chrome_version}")
                logger.error("Please download the correct ChromeDriver version from:")
                logger.error("https://googlechromelabs.github.io/chrome-for-testing/")
                logger.error(f"Look for version {chrome_version}")
                logger.error("After downloading:")
                logger.error("1. Extract the chromedriver.exe file")
                logger.error("2. Replace the existing chromedriver.exe in your project directory")
                logger.error("3. Make sure it's the 64-bit version")
            raise

        download_links = set()
        
        try:
            logger.info(f"Accessing URL: {website}")
            driver.get(website)
            
            # Wait for the page to load
            logger.info("Waiting for page to load...")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            logger.info("Page loaded successfully")
            
            # Get page source and parse with BeautifulSoup
            logger.info("Parsing page content...")
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all links
            links = soup.find_all('a', href=True)
            logger.info(f"Found {len(links)} total links on page")
            
            # Process each link
            for link in links:
                href = link.get('href')
                if href:
                    href = get_absolute_url(website, href)
                    if not href:
                        continue
                        
                    logger.info(f"Processing link: {href}")
                    
                    # Check if it's a download link
                    if is_download_link(href):
                        logger.info(f"✅ Found PDF download link: {href}")
                        download_links.add(href)
                    else:
                        logger.info(f"⏭️ Skipping non-PDF link: {href}")
            
            # Also check for download links in the page content
            logger.info("Checking page content for additional PDF links...")
            download_elements = driver.find_elements(By.XPATH, "//*[contains(@href, 'download') or contains(@href, '.pdf')]")
            for element in download_elements:
                href = element.get_attribute('href')
                if href:
                    href = get_absolute_url(website, href)
                    if href:
                        logger.info(f"✅ Found PDF link from element: {href}")
                        download_links.add(href)
            
            logger.info(f"Scraping completed. Found {len(download_links)} PDF links")
            return list(download_links)
            
        except Exception as e:
            logger.error(f"An error occurred during scraping: {str(e)}")
            raise
        finally:
            driver.quit()
            logger.info("Browser closed.")
            
    except Exception as e:
        logger.error(f"Critical error in scrape_website: {str(e)}")
        raise

@retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
def download_pdf(pdf_url, download_folder="downloads"):
    """
    Downloads a PDF file from the given URL to the specified folder.
    Uses retry mechanism for failed downloads.
    """
    try:
        logger.info(f"Starting download from: {pdf_url}")
        
        # Create download folder if it doesn't exist
        download_folder = create_download_folder(download_folder)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/pdf,application/x-pdf,application/octet-stream',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': pdf_url
        }
        
        # First, make a HEAD request to check the content type
        logger.info("Checking content type...")
        head_response = requests.head(pdf_url, headers=headers, allow_redirects=True, timeout=10)
        content_type = head_response.headers.get('Content-Type', '').lower()
        
        # If it's not a PDF, try to follow the redirect
        if 'application/pdf' not in content_type and 'application/octet-stream' not in content_type:
            logger.info(f"Following redirect for: {pdf_url}")
            response = requests.get(pdf_url, headers=headers, stream=True, allow_redirects=True, timeout=30)
        else:
            response = requests.get(pdf_url, headers=headers, stream=True, timeout=30)
            
        response.raise_for_status()
        
        # Get filename from URL or response headers
        filename = get_filename_from_url(pdf_url, response)
        logger.info(f"Downloading file as: {filename}")
        
        filepath = os.path.join(download_folder, filename)
        
        # Download the file in chunks
        logger.info("Downloading file content...")
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    
        logger.info(f"✅ Successfully downloaded: {filename}")
        return filepath

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error downloading {pdf_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error downloading {pdf_url}: {e}")
        return None

def extract_body_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    body_content = soup.body
    if body_content:
        return str(body_content)
    return ""


def clean_body_content(body_content):
    soup = BeautifulSoup(body_content, 'html.parser')
    for script_or_style in soup(['script', 'style']):
        script_or_style.extract()

    cleaned_content = soup.get_text(separator='\n')
    cleaned_content = "\n".join(line.strip() for line in cleaned_content.splitlines() if line.strip())
    return cleaned_content


def split_dom_content(dom_content, max_length=6000):
    return [
        dom_content[i:i + max_length] for i in range(0, len(dom_content), max_length)
    ]

def scrape_website_content(url):
    """
    Scrape all visible content from a website URL.
    Returns structured data including text, images, and titles.
    """
    try:
        logger.info(f"Starting website content scraping for: {url}")
        
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # options.add_argument("--headless=new")  # Commented out headless mode
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument(f"user-agent={get_random_user_agent()}")
        
        try:
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {str(e)}")
            raise
        
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Add a small delay to let dynamic content load
            time.sleep(2)
            
            # Get page source and parse with BeautifulSoup
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract structured data
            data = {
                'title': soup.title.string if soup.title else '',
                'headings': [],
                'paragraphs': [],
                'images': [],
                'links': [],
                'metadata': {
                    'url': url,
                    'scraped_date': datetime.now().isoformat(),
                    'user_agent': get_random_user_agent()
                }
            }
            
            # Extract headings
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                data['headings'].append({
                    'level': heading.name,
                    'text': heading.get_text(strip=True)
                })
            
            # Extract paragraphs
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if text:
                    data['paragraphs'].append(text)
            
            # Extract images with rate limiting
            for img in soup.find_all('img'):
                src = img.get('src', '')
                alt = img.get('alt', '')
                if src:
                    rate_limit()  # Add delay between image processing
                    data['images'].append({
                        'src': get_absolute_url(url, src),
                        'alt': alt
                    })
            
            # Extract links
            for a in soup.find_all('a', href=True):
                href = a.get('href')
                text = a.get_text(strip=True)
                if href:
                    data['links'].append({
                        'url': get_absolute_url(url, href),
                        'text': text
                    })
            
            return data
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"Error in scrape_website_content: {str(e)}")
        raise

def scrape_for_pdf(url):
    """
    Extract and structure data specifically for PDF generation.
    Returns clean, structured content optimized for PDF creation.
    """
    try:
        logger.info(f"Starting PDF-specific scraping for: {url}")
        
        # First get the website content
        content = scrape_website_content(url)
        
        # Structure the content for PDF generation
        pdf_data = {
            'title': content['title'],
            'sections': [],
            'images': content['images'],
            'metadata': {
                'source_url': url,
                'scraped_date': datetime.now().isoformat(),
                'user_agent': get_random_user_agent()
            }
        }
        
        # Organize content into sections based on headings
        current_section = None
        for element in content['headings'] + [{'type': 'p', 'text': p} for p in content['paragraphs']]:
            if 'level' in element:  # It's a heading
                if current_section:
                    pdf_data['sections'].append(current_section)
                current_section = {
                    'heading': element['text'],
                    'level': element['level'],
                    'content': []
                }
            elif current_section and element['text']:
                current_section['content'].append(element['text'])
        
        # Add the last section if exists
        if current_section:
            pdf_data['sections'].append(current_section)
        
        return pdf_data
        
    except Exception as e:
        logger.error(f"Error in scrape_for_pdf: {str(e)}")
        raise



