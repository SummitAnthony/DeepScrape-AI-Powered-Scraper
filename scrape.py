from bs4 import BeautifulSoup as BeautifulSoup
import time
import os
import requests
import urllib.parse
import re
import json
import logging
from retrying import retry
import hashlib
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import random
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

def get_random_user_agent():
    """Get a random user agent from the list"""
    return random.choice(USER_AGENTS)

def rate_limit():
    """Add a random delay between requests to avoid rate limiting"""
    delay = RATE_LIMIT_DELAY + random.uniform(0, 1)
    time.sleep(delay)

def fetch_html(url, timeout=15):
    """Fetch page HTML with plain requests (fast path).
    Returns HTML string, or None if the caller should fall back to the headless browser."""
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        if 'html' not in response.headers.get('Content-Type', '').lower():
            return None
        return response.text
    except Exception as e:
        logger.info(f"requests fetch failed ({e}); trying TLS-impersonation tier")
        return None

def fetch_html_impersonate(url, proxy=None):
    """Fetch HTML impersonating a real browser's TLS fingerprint via curl_cffi.
    Returns HTML string, or None to fall back to the headless browser."""
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        logger.info("curl_cffi not installed; skipping impersonation tier")
        return None
    try:
        proxies = {"http": proxy, "https": proxy} if proxy else None
        response = cffi_requests.get(url, impersonate="chrome", timeout=20, proxies=proxies)
        response.raise_for_status()
        if 'html' not in response.headers.get('Content-Type', '').lower():
            return None
        return response.text
    except Exception as e:
        logger.info(f"impersonation fetch failed ({e}); falling back to headless browser")
        return None

def load_proxies(path="proxies.txt"):
    """Load a proxy list (one per line, # comments allowed). Missing file -> []."""
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

class ProxyRotator:
    """Round-robin over a proxy pool. next() returns None when the pool is empty."""
    def __init__(self, proxies):
        self.proxies = list(proxies)
        self._i = 0
    def next(self):
        if not self.proxies:
            return None
        proxy = self.proxies[self._i % len(self.proxies)]
        self._i += 1
        return proxy

# Module-level rotator, populated from proxies.txt at import
_proxy_rotator = ProxyRotator(load_proxies())

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

# Page cache: URL hash -> HTML on disk, with TTL
CACHE_DIR = ".page_cache"
CACHE_TTL = 3600  # seconds

def _cache_path(url):
    return os.path.join(CACHE_DIR, hashlib.md5(url.encode()).hexdigest() + ".html")

def _cache_get(url):
    try:
        path = _cache_path(url)
        if os.path.exists(path) and time.time() - os.path.getmtime(path) < CACHE_TTL:
            with open(path, 'r', encoding='utf-8') as f:
                logger.info(f"Cache hit: {url}")
                return f.read()
    except Exception as e:
        logger.warning(f"Cache read failed: {str(e)}")
    return None

def _cache_put(url, html):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(_cache_path(url), 'w', encoding='utf-8') as f:
            f.write(html)
    except Exception as e:
        logger.warning(f"Cache write failed: {str(e)}")

def _browser_fetch(url):
    """Fetch fully rendered HTML with headless Chromium via Playwright."""
    from playwright.sync_api import sync_playwright
    logger.info("Launching headless Chromium (Playwright)...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=get_random_user_agent())
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)  # let dynamic content load
            return page.content()
        finally:
            browser.close()

def get_page_html(website, use_cache=True, browser_fetcher=None):
    """Get page HTML through tiers: cache -> requests -> TLS impersonation -> headless browser."""
    if use_cache:
        cached = _cache_get(website)
        if cached is not None:
            return cached

    html = fetch_html(website)
    if html is not None:
        logger.info("Fetched page via requests (fast path)")
    else:
        html = fetch_html_impersonate(website, proxy=_proxy_rotator.next())
        if html is not None:
            logger.info("Fetched page via TLS impersonation")
        else:
            fetcher = browser_fetcher or _browser_fetch
            html = fetcher(website)

    _cache_put(website, html)
    return html

@retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
def scrape_website(website):
    """Scrape website for PDF download links (requests first, headless browser fallback)"""
    try:
        logger.info(f"Starting scraping process for: {website}")
        html = get_page_html(website)
        soup = BeautifulSoup(html, 'html.parser')

        download_links = set()
        # Any element with an href (not just <a>) that looks like a PDF/download link
        for element in soup.find_all(href=True):
            href = get_absolute_url(website, element.get('href'))
            if href and is_download_link(href):
                download_links.add(href)

        logger.info(f"Scraping completed. Found {len(download_links)} PDF links")
        return list(download_links)

    except Exception as e:
        logger.error(f"Critical error in scrape_website: {str(e)}")
        raise

_robots_cache = {}

def is_allowed_by_robots(url, user_agent='*'):
    """Check robots.txt for the URL's domain (cached). Permissive on failure."""
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base not in _robots_cache:
            rp = RobotFileParser()
            rp.set_url(base + "/robots.txt")
            try:
                rp.read()
            except Exception:
                rp = None
            _robots_cache[base] = rp
        rp = _robots_cache[base]
        return True if rp is None else rp.can_fetch(user_agent, url)
    except Exception:
        return True

def crawl_website(start_url, max_depth=1, max_pages=20):
    """BFS crawl of same-domain links up to max_depth, collecting PDF links.
    Respects robots.txt. Returns {'pages': [urls visited], 'pdf_links': [...]}"""
    domain = urlparse(start_url).netloc
    seen = {start_url}
    queue = [(start_url, 0)]
    pdf_links = set()
    pages = []

    while queue and len(pages) < max_pages:
        url, depth = queue.pop(0)
        if not is_allowed_by_robots(url):
            logger.info(f"Skipping (robots.txt): {url}")
            continue
        try:
            html = get_page_html(url)
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {str(e)}")
            continue
        pages.append(url)
        logger.info(f"Crawled ({depth}): {url}")

        soup = BeautifulSoup(html, 'html.parser')
        for element in soup.find_all(href=True):
            href = get_absolute_url(url, element.get('href'))
            if not href:
                continue
            if is_download_link(href):
                pdf_links.add(href)
            elif depth < max_depth and urlparse(href).netloc == domain:
                clean = href.split('#')[0]
                if clean not in seen:
                    seen.add(clean)
                    queue.append((clean, depth + 1))
        if queue:
            rate_limit()

    logger.info(f"Crawl done: {len(pages)} pages, {len(pdf_links)} PDF links")
    return {'pages': pages, 'pdf_links': list(pdf_links)}

def extract_candidate_links(html, base_url, domain):
    """Extract same-domain links as (url, link_text) pairs, deduped, fragments stripped."""
    soup = BeautifulSoup(html, 'html.parser')
    seen = set()
    candidates = []
    for a in soup.find_all('a', href=True):
        href = get_absolute_url(base_url, a.get('href'))
        if not href:
            continue
        href = href.split('#')[0]
        if not href or urlparse(href).netloc != domain or href in seen:
            continue
        seen.add(href)
        candidates.append((href, a.get_text(strip=True)[:120]))
    return candidates

def parse_ranked_indices(text, n_candidates):
    """Parse an LLM response like '[2, 0, 5]' into valid, deduped candidate indices."""
    match = re.search(r'\[[\d,\s]*\]', text)
    if not match:
        return []
    try:
        indices = json.loads(match.group(0))
    except ValueError:
        return []
    out = []
    for i in indices:
        if isinstance(i, int) and 0 <= i < n_candidates and i not in out:
            out.append(i)
    return out

def llm_rank_links(goal, candidates, model=None, top_n=8):
    """Ask the LLM which candidate links best serve the goal. Returns ordered indices."""
    import asyncio
    import parse as parse_mod
    listing = "\n".join(f"{i}: {text or '(no text)'} — {url}" for i, (url, text) in enumerate(candidates))
    prompt = f"""You are guiding a focused web crawler. The user's goal: {goal}

Candidate links:
{listing}

Return ONLY a JSON array of the indices (integers) of up to {top_n} links most likely to help achieve the goal, best first. Example: [3, 0, 7]. Return [] if none are relevant."""
    response = asyncio.run(parse_mod._generate(prompt, model or parse_mod.MODEL_NAME))
    return parse_ranked_indices(response, len(candidates))

def smart_crawl(start_url, goal, max_depth=1, max_pages=15, ranker=None, model=None):
    """Goal-directed crawl: at each page the LLM picks which same-domain links to follow.
    Returns {'pages': [urls visited], 'pdf_links': [...]}"""
    if ranker is None:
        ranker = lambda g, cands: llm_rank_links(g, cands, model)
    domain = urlparse(start_url).netloc
    seen = {start_url}
    queue = [(start_url, 0)]
    pdf_links = set()
    pages = []

    while queue and len(pages) < max_pages:
        url, depth = queue.pop(0)
        if not is_allowed_by_robots(url):
            logger.info(f"Skipping (robots.txt): {url}")
            continue
        try:
            html = get_page_html(url)
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {str(e)}")
            continue
        pages.append(url)

        soup = BeautifulSoup(html, 'html.parser')
        for element in soup.find_all(href=True):
            href = get_absolute_url(url, element.get('href'))
            if href and is_download_link(href):
                pdf_links.add(href)

        if depth < max_depth:
            candidates = [(u, t) for u, t in extract_candidate_links(html, url, domain)
                          if u not in seen and not is_download_link(u)]
            if candidates:
                for idx in ranker(goal, candidates):
                    chosen = candidates[idx][0]
                    if chosen not in seen:
                        seen.add(chosen)
                        queue.append((chosen, depth + 1))
        if queue:
            rate_limit()

    logger.info(f"Smart crawl done: {len(pages)} pages, {len(pdf_links)} PDF links")
    return {'pages': pages, 'pdf_links': list(pdf_links)}

def download_pdfs_concurrent(pdf_links, download_folder="downloads", max_workers=4, progress_callback=None):
    """Download PDFs concurrently. Returns (successful_filepaths, failed_links)."""
    successful, failed = [], []
    if not pdf_links:
        return successful, failed
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(download_pdf, link, download_folder): link for link in pdf_links}
        done = 0
        for future in as_completed(futures):
            link = futures[future]
            done += 1
            try:
                filepath = future.result()
            except Exception as e:
                logger.error(f"Download failed for {link}: {str(e)}")
                filepath = None
            if filepath:
                successful.append(filepath)
            else:
                failed.append(link)
            if progress_callback:
                progress_callback(done, len(futures))
    return successful, failed

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

        html = get_page_html(url)
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
        
        # Extract images
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            if src:
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



