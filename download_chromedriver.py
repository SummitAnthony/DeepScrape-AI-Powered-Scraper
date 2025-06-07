import requests
import zipfile
import io
import os
import logging
import winreg
import subprocess
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_chrome_version():
    """Get the installed Chrome version"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        return version
    except Exception as e:
        logger.error(f"Error getting Chrome version from registry: {str(e)}")
        try:
            chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            if os.path.exists(chrome_path):
                result = subprocess.run([chrome_path, '--version'], capture_output=True, text=True)
                version = result.stdout.strip().split()[-1]
                return version
        except Exception as e2:
            logger.error(f"Error getting Chrome version from executable: {str(e2)}")
        return None

def download_chromedriver(force_version=None):
    """Download the correct ChromeDriver version"""
    chrome_version = force_version or get_chrome_version()
    if not chrome_version:
        logger.error("Could not determine Chrome version")
        return False
    
    logger.info(f"Using Chrome version: {chrome_version}")
    
    # Try different base URLs
    base_urls = [
        "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing",
        "https://chromedriver.storage.googleapis.com"
    ]
    
    platform = "win64"
    success = False
    
    for base_url in base_urls:
        try:
            if "edgedl.me.gvt1.com" in base_url:
                url = f"{base_url}/{chrome_version}/{platform}/chromedriver-{platform}.zip"
            else:
                # For older versions
                major_version = chrome_version.split('.')[0]
                url = f"{base_url}/{major_version}.0.7151.68/chromedriver_win32.zip"
            
            logger.info(f"Attempting to download from: {url}")
            response = requests.get(url)
            response.raise_for_status()
            
            # Extract the zip file
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                # Find chromedriver.exe in the zip
                chromedriver_path = None
                for file in zip_file.namelist():
                    if file.endswith('chromedriver.exe'):
                        chromedriver_path = file
                        break
                
                if not chromedriver_path:
                    logger.error("Could not find chromedriver.exe in the downloaded zip")
                    continue
                
                # Extract chromedriver.exe
                logger.info("Extracting chromedriver.exe...")
                zip_file.extract(chromedriver_path)
                
                # Move it to the current directory
                extracted_path = os.path.join(os.getcwd(), chromedriver_path)
                target_path = os.path.join(os.getcwd(), "chromedriver.exe")
                
                if os.path.exists(target_path):
                    os.remove(target_path)
                
                os.rename(extracted_path, target_path)
                logger.info(f"ChromeDriver installed successfully at: {target_path}")
                success = True
                break
                
        except Exception as e:
            logger.error(f"Error with {base_url}: {str(e)}")
            continue
    
    return success

if __name__ == "__main__":
    # Use the specific version you provided
    if download_chromedriver(force_version="137.0.7151.68"):
        logger.info("ChromeDriver installation completed successfully!")
    else:
        logger.error("ChromeDriver installation failed!")
        sys.exit(1) 