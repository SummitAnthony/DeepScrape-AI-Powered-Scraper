"""Vision analysis: screenshot a page and analyze it with a multimodal model (llava) via Ollama."""
import base64
import logging

import requests

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
DEFAULT_VISION_MODEL = "llava"


def encode_image_bytes(data):
    """Base64-encode raw image bytes to an ASCII string."""
    return base64.b64encode(data).decode()


def build_vision_payload(prompt, image_bytes, model=None):
    """Build the Ollama /api/generate payload for a vision request."""
    return {
        "model": model or DEFAULT_VISION_MODEL,
        "prompt": prompt,
        "images": [encode_image_bytes(image_bytes)],
        "stream": False,
    }


def analyze_image(image_bytes, prompt, model=None):
    """Send an image + prompt to the vision model. Returns the response text or an error string."""
    payload = build_vision_payload(prompt, image_bytes, model)
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=300)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Vision analysis failed: {str(e)}")
        return f"Error analyzing image: {str(e)}. Make sure a vision model (e.g. '{model or DEFAULT_VISION_MODEL}') is pulled in Ollama."
    try:
        return response.json().get("response", "").strip() or "Error: empty response from vision model"
    except ValueError:
        return "Error: invalid response from vision model"


def screenshot_page(url):
    """Capture a full-page PNG screenshot via Playwright. Returns raw bytes."""
    from scrape import get_random_user_agent
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=get_random_user_agent())
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            return page.screenshot(full_page=True)
        finally:
            browser.close()
