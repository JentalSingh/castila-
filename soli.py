# hn_form_upload_final_working.py
"""
HOSPITAL NACIONAL DE PARAPLÉJICOS - PDF UPLOADER (FINAL WORKING)
Properly extracts the uploaded PDF URL from page source
"""

import os
import time
import logging
import random
import re
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv
from faker import Faker
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

load_dotenv()

# ============================================================
# PATH HANDLING
# ============================================================
SCRIPT_DIR = Path(__file__).parent.absolute()
os.chdir(SCRIPT_DIR)

PROXY_FILE = SCRIPT_DIR / "proxies.txt"
PDF_NAME = "ilt4.pdf"
PDF_PATH = SCRIPT_DIR / PDF_NAME
LOG_FILE = SCRIPT_DIR / "hn_fetcher.log"
RESULT_FILE = SCRIPT_DIR / "hn_pdf_url.txt"

# ============================================================
# LOGGING SETUP
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8")
    ]
)
logger = logging.getLogger("hn_pdf_fetcher")

# ============================================================
# CONFIGURATION
# ============================================================
TARGET_URL = "https://hnparaplejicos.sanidad.castillalamancha.es/en/node/34105"
PDF_DOMAIN = "hnparaplejicos.sanidad.castillalamancha.es"
PDF_PATH_PATTERN = "/sites/hnparaplejicos.sescam.castillalamancha.es/files/webform/"

fake = Faker()

# ============================================================
# PROXY FUNCTIONS
# ============================================================
def load_proxies():
    proxies = []
    if PROXY_FILE.exists():
        with open(PROXY_FILE, "r", encoding="utf-8") as handle:
            for line in handle:
                value = line.strip()
                if value and not value.startswith("#"):
                    proxies.append(value)
        logger.info(f"✅ Loaded {len(proxies)} proxies from {PROXY_FILE}")
    return proxies

def parse_proxy(proxy_str):
    if not proxy_str:
        return None
    proxy_str = proxy_str.replace('http://', '').replace('https://', '')
    try:
        parts = proxy_str.split(':')
        if len(parts) == 4:
            host, port, username, password = parts
            return {
                "server": f"http://{host}:{port}",
                "username": username,
                "password": password,
                "host": host,
                "port": port
            }
        elif len(parts) == 2:
            host, port = parts
            return {"server": f"http://{host}:{port}"}
        return None
    except:
        return None

def get_random_proxy():
    proxies = load_proxies()
    if not proxies:
        logger.error("❌ No proxies found!")
        return None
    shuffled = proxies[:]
    random.shuffle(shuffled)
    for proxy_str in shuffled[:50]:
        proxy_config = parse_proxy(proxy_str)
        if proxy_config:
            logger.info(f"🔄 Using proxy: {proxy_str[:30]}...")
            return proxy_config
    return None

# ============================================================
# PDF FUNCTIONS
# ============================================================
def create_pdf_if_not_exists():
    if PDF_PATH.exists():
        logger.info(f"✅ PDF exists: {PDF_PATH}")
        return PDF_PATH
    try:
        c = canvas.Canvas(str(PDF_PATH), pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(100, 750, "DOCUMENTO DE PRUEBA")
        c.drawString(100, 730, "=" * 50)
        c.drawString(100, 710, f"Fecha: {time.strftime('%Y-%m-%d')}")
        c.drawString(100, 690, f"Nombre: {fake.name()}")
        c.save()
        logger.info(f"✅ Created PDF: {PDF_PATH}")
        return PDF_PATH
    except Exception as e:
        logger.error(f"❌ PDF creation error: {e}")
        return None

# ============================================================
# URL EXTRACTION - ✅ FIXED
# ============================================================
def extract_pdf_url_from_page(page):
    """Extract PDF URL from page source"""
    try:
        html = page.content()
        
        # Pattern 1: Full URL with ilt4_
        pattern1 = r'https://hnparaplejicos\.sanidad\.castillalamancha\.es/sites/hnparaplejicos\.sescam\.castillalamancha\.es/files/webform/ilt4_\d+\.pdf'
        match = re.search(pattern1, html)
        if match:
            url = match.group(0)
            logger.info(f"✅ Found PDF URL: {url}")
            return url
        
        # Pattern 2: Any ilt4.pdf in webform
        pattern2 = r'/sites/hnparaplejicos\.sescam\.castillalamancha\.es/files/webform/ilt4[^"]*\.pdf'
        match = re.search(pattern2, html)
        if match:
            url = f"https://hnparaplejicos.sanidad.castillalamancha.es{match.group(0)}"
            logger.info(f"✅ Found PDF URL: {url}")
            return url
        
        # Pattern 3: Any PDF in webform
        pattern3 = r'/sites/hnparaplejicos\.sescam\.castillalamancha\.es/files/webform/[^"]+\.pdf'
        match = re.search(pattern3, html)
        if match:
            url = f"https://hnparaplejicos.sanidad.castillalamancha.es{match.group(0)}"
            if 'ilt4' in url:
                logger.info(f"✅ Found PDF URL: {url}")
                return url
        
        return None
    except Exception as e:
        logger.error(f"Page source search error: {e}")
        return None

def extract_pdf_url_from_ajax_response(page):
    """Extract PDF URL from AJAX network responses"""
    try:
        # Wait for AJAX response
        time.sleep(2)
        
        # Get all responses
        responses = page.evaluate("""
            () => {
                let urls = [];
                performance.getEntries().forEach(entry => {
                    if (entry.name && entry.name.includes('.pdf')) {
                        urls.push(entry.name);
                    }
                });
                return urls;
            }
        """)
        
        for url in responses:
            if 'ilt4' in url:
                logger.info(f"✅ Found PDF URL from AJAX: {url}")
                return url
        
        return None
    except:
        return None

# ============================================================
# MAIN FUNCTION
# ============================================================
def fetch_pdf_from_hn_form():
    """Main function"""
    
    logger.info("=" * 60)
    logger.info("🏥 HN PARAPLÉJICOS - PDF UPLOADER")
    logger.info("=" * 60)
    
    # ===== STEP 1: Get Proxy =====
    proxy_config = get_random_proxy()
    if not proxy_config:
        return False, None, "No valid proxy found!"
    
    logger.info(f"✅ Proxy: {proxy_config['server']}")
    
    # ===== STEP 2: Check PDF =====
    pdf_path = create_pdf_if_not_exists()
    if not pdf_path:
        return False, None, "Could not create PDF!"
    
    # ===== STEP 3: Chrome path =====
    chrome_paths = [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        os.path.expanduser("~") + "\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"
    ]
    chrome_path = next((p for p in chrome_paths if os.path.exists(p)), None)
    if not chrome_path:
        return False, None, "Chrome not found!"
    
    # ===== STEP 4: Clean Profile =====
    profile_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "HN_PDF_Profile")
    if os.path.exists(profile_dir):
        try:
            shutil.rmtree(profile_dir)
        except:
            pass
    
    # ===== STEP 5: Launch Browser =====
    with sync_playwright() as p:
        context_kwargs = {
            "user_data_dir": profile_dir,
            "executable_path": chrome_path,
            "headless": False,
            "viewport": {'width': 1366, 'height': 768},
            "args": ["--disable-blink-features=AutomationControlled"]
        }
        
        proxy_dict = {"server": proxy_config["server"]}
        if proxy_config.get("username"):
            proxy_dict["username"] = proxy_config["username"]
            proxy_dict["password"] = proxy_config["password"]
        context_kwargs["proxy"] = proxy_dict
        
        context = p.chromium.launch_persistent_context(**context_kwargs)
        page = context.new_page()
        
        try:
            # ===== STEP 6: Navigate =====
            logger.info("🌐 Navigating to form...")
            page.goto(TARGET_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(3)
            
            # ===== STEP 7: Upload PDF =====
            logger.info("📎 Uploading PDF...")
            file_input = page.locator('input#edit-submitted-adjuntar-informacion-upload').first
            if not file_input or not file_input.is_visible(timeout=3000):
                file_input = page.locator('input[type="file"]').first
            
            if file_input and file_input.is_visible(timeout=3000):
                file_input.set_input_files(str(pdf_path))
                logger.info("✅ PDF uploaded!")
                time.sleep(3)
            else:
                context.close()
                return False, None, "File input not found!"
            
            # ===== STEP 8: Click Upload Button =====
            logger.info("🔼 Clicking Upload button...")
            upload_btn = page.locator('input[value="Upload"]').first
            if upload_btn and upload_btn.is_visible(timeout=2000):
                upload_btn.click()
                logger.info("✅ Upload button clicked!")
                time.sleep(5)
            else:
                logger.info("ℹ️ No Upload button, waiting...")
                time.sleep(3)
            
            # ===== STEP 9: Extract PDF URL =====
            logger.info("🔍 Extracting PDF URL...")
            
            # Try page source first
            pdf_url = extract_pdf_url_from_page(page)
            
            # If not found, try AJAX
            if not pdf_url:
                pdf_url = extract_pdf_url_from_ajax_response(page)
            
            # If still not found, check page source again after delay
            if not pdf_url:
                logger.info("⏳ Waiting for page to update...")
                time.sleep(5)
                pdf_url = extract_pdf_url_from_page(page)
            
            # ===== STEP 10: Result =====
            if pdf_url:
                with open(RESULT_FILE, "w", encoding="utf-8") as f:
                    f.write(f"PDF URL: {pdf_url}\n")
                    f.write(f"PDF File: {PDF_NAME}\n")
                    f.write(f"Proxy: {proxy_config['server']}\n")
                    f.write(f"Status: SUCCESS\n")
                    f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                print("\n" + "=" * 60)
                print("✅ SUCCESS! PDF URL FOUND")
                print("=" * 60)
                print(f"🔗 PDF URL: {pdf_url}")
                print("=" * 60 + "\n")
                
                page.screenshot(path=str(SCRIPT_DIR / "upload_success.png"))
                context.close()
                return True, pdf_url, None
            else:
                error_msg = "No PDF URL found in page source or network"
                logger.error(f"❌ {error_msg}")
                
                page.screenshot(path=str(SCRIPT_DIR / "upload_failed.png"))
                with open(SCRIPT_DIR / "page_source_debug.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                
                context.close()
                return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Error: {e}"
            logger.error(f"❌ {error_msg}")
            context.close()
            return False, None, error_msg

# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🏥 HN PARAPLÉJICOS - PDF UPLOADER")
    print("=" * 60)
    print(f"📄 PDF: {PDF_NAME}")
    print(f"🔗 URL: {TARGET_URL}")
    print("=" * 60 + "\n")
    
    success, pdf_url, error = fetch_pdf_from_hn_form()
    
    if success:
        print(f"✅ SUCCESS! PDF URL: {pdf_url}")
    else:
        print(f"❌ FAILED: {error}")