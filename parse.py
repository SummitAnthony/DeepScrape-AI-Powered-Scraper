import aiohttp
import json
import os
import PyPDF2
import io
import asyncio
from retrying import retry
import logging
from pathlib import Path
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Try to import PyMuPDF, but don't fail if it's not available
try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    logger.warning("PyMuPDF not available. Using PyPDF2 as fallback.")
    PYMUPDF_AVAILABLE = False

# Ollama API configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama2"  # Changed to llama2 as it's more commonly available

def check_ollama_availability():
    """Check if Ollama is running and available"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            # Try to get the list of models
            models = response.json().get('models', [])
            if not any(model['name'] == MODEL_NAME for model in models):
                return False, f"Model {MODEL_NAME} is not available. Please run 'ollama pull {MODEL_NAME}'"
            return True, "Ollama is running and model is available"
        return False, "Ollama is not responding correctly"
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to Ollama. Please make sure Ollama is running (ollama serve)"
    except Exception as e:
        return False, f"Error connecting to Ollama: {str(e)}"

def get_ollama_status():
    """Get detailed status about Ollama availability"""
    available, message = check_ollama_availability()
    if not available:
        return {
            "available": False,
            "message": f"Ollama is not ready: {message}"
        }
    return {
        "available": True,
        "message": message
    }

def clean_text(text):
    """Clean extracted text by removing extra whitespace and normalizing line breaks"""
    if not text:
        return ""
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    # Replace multiple newlines with single newline
    text = re.sub(r'\n+', '\n', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text

@retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
async def extract_text_from_pdf(pdf_path):
    """Extract text content from a PDF file with retry mechanism and multiple extraction methods"""
    try:
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return ""
            
        text = ""
        
        # Try PyMuPDF (fitz) first if available
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(pdf_path)
                for page in doc:
                    text += page.get_text()
                doc.close()
                text = clean_text(text)
                if text.strip():
                    return text
            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed: {str(e)}")
        
        # Fallback to PyPDF2
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract text from all pages
                for page in pdf_reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as e:
                        logger.error(f"Error extracting text from page: {str(e)}")
                        continue
                
                text = clean_text(text)
                if text.strip():
                    return text
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {str(e)}")
        
        # If both methods fail, try to extract text from PDF metadata
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                if pdf_reader.metadata:
                    metadata_text = ""
                    for key, value in pdf_reader.metadata.items():
                        if value:
                            metadata_text += f"{key}: {value}\n"
                    if metadata_text:
                        return clean_text(metadata_text)
        except Exception as e:
            logger.error(f"Metadata extraction failed: {str(e)}")
        
        logger.error(f"All text extraction methods failed for {pdf_path}")
        return ""
            
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
        return ""

async def process_pdf_files(pdf_paths):
    """Process multiple PDF files concurrently"""
    tasks = [extract_text_from_pdf(path) for path in pdf_paths]
    results = await asyncio.gather(*tasks)
    return results

@retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
async def parse_with_ollama(pdf_paths, description):
    """
    Parse the content using Ollama API based on the provided description.
    Uses async/await for better performance and retry mechanism for reliability.
    """
    logger.info("Starting parse_with_ollama function")
    
    # Check if Ollama is available
    available, message = check_ollama_availability()
    if not available:
        logger.error(f"Ollama is not available: {message}")
        return message

    # Prepare the prompt for the API
    prompt = f"""Analyze the following content and provide a response based on the user's instructions:

{description}

Provide a clear, well-formatted response that directly addresses the user's request."""

    logger.info(f"Preparing to send request to Ollama API with model: {MODEL_NAME}")
    data = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 4000,
            "top_p": 0.9,
            "top_k": 40
        }
    }

    try:
        logger.info("Sending request to Ollama API...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OLLAMA_API_URL,
                json=data,
                timeout=300,
                headers={"Content-Type": "application/json"}
            ) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                
                if response.status != 200:
                    logger.error(f"API error: {response.status} - {response_text}")
                    return f"API error: {response.status}. Please make sure Ollama is running and the model is downloaded."
                
                try:
                    result = json.loads(response_text)
                    if 'response' not in result:
                        return "Error: Unexpected response format from Ollama API"
                    return result['response'].strip()
                except json.JSONDecodeError as e:
                    return f"Error: Invalid response from Ollama API - {response_text[:100]}"
                    
    except asyncio.TimeoutError:
        return "Error: The request timed out. Please try again with a more specific question or less content."
    except Exception as e:
        return f"Error analyzing content: {str(e)}. Please make sure Ollama is running and properly configured."

# Synchronous wrapper for Streamlit compatibility
def sync_parse_with_deepseek(pdf_paths, description):
    """Synchronous wrapper for async parse function"""
    try:
        logger.info("Starting sync_parse_with_deepseek")
        logger.info(f"Description: {description[:100]}...")  # Log first 100 chars of description
        result = asyncio.run(parse_with_ollama(pdf_paths, description))
        logger.info("Successfully completed sync_parse_with_deepseek")
        logger.info(f"Result: {result[:100]}...")  # Log first 100 chars of result
        return result
    except Exception as e:
        logger.error(f"Error in sync_parse_with_deepseek: {str(e)}")
        return f"Error: {str(e)}"

