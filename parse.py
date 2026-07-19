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

def get_available_models():
    """Return the list of locally installed Ollama model names (empty if unreachable)"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            return [m['name'] for m in response.json().get('models', [])]
    except Exception as e:
        logger.warning(f"Could not list Ollama models: {str(e)}")
    return []

def check_ollama_availability(model=None):
    """Check if Ollama is running and the model is available"""
    model = model or MODEL_NAME
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            # Try to get the list of models
            models = response.json().get('models', [])
            if not any(m['name'] == model for m in models):
                return False, f"Model {model} is not available. Please run 'ollama pull {model}'"
            return True, f"Ollama is running and model {model} is available"
        return False, "Ollama is not responding correctly"
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to Ollama. Please make sure Ollama is running (ollama serve)"
    except Exception as e:
        return False, f"Error connecting to Ollama: {str(e)}"

def get_ollama_status(model=None):
    """Get detailed status about Ollama availability"""
    available, message = check_ollama_availability(model)
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

async def _generate(prompt, model):
    """Single Ollama generate call. Returns response text (or an error string)."""
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 4000,
            "top_p": 0.9,
            "top_k": 40
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            OLLAMA_API_URL,
            json=data,
            timeout=300,
            headers={"Content-Type": "application/json"}
        ) as response:
            response_text = await response.text()
            if response.status != 200:
                logger.error(f"API error: {response.status} - {response_text}")
                return f"API error: {response.status}. Please make sure Ollama is running and the model is downloaded."
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                return f"Error: Invalid response from Ollama API - {response_text[:100]}"
            if 'response' not in result:
                return "Error: Unexpected response format from Ollama API"
            return result['response'].strip()

# Max characters of content per LLM call (rough context-window budget)
MAX_CONTENT_CHARS = 24000

async def parse_large_content(content, instructions, model=None, progress_callback=None):
    """Map-reduce analysis: split oversized content into chunks, analyze each,
    then combine the partial results into one response."""
    model = model or MODEL_NAME
    available, message = check_ollama_availability(model)
    if not available:
        return message

    chunks = [content[i:i + MAX_CONTENT_CHARS] for i in range(0, len(content), MAX_CONTENT_CHARS)] or [""]

    try:
        if len(chunks) == 1:
            prompt = f"""Content to analyze:
{content}

User's instructions: {instructions}

Provide a clear, well-formatted response that directly addresses the user's request."""
            return await _generate(prompt, model)

        # Map: analyze each chunk independently
        partial_results = []
        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(i + 1, len(chunks))
            prompt = f"""This is part {i + 1} of {len(chunks)} of a larger document. Extract and summarize everything relevant to the user's instructions from this part only.

Content:
{chunk}

User's instructions: {instructions}"""
            partial_results.append(await _generate(prompt, model))

        # Reduce: merge partial analyses
        combined = "\n\n".join(partial_results)[:MAX_CONTENT_CHARS]
        reduce_prompt = f"""Below are partial analyses of consecutive parts of one document. Merge them into a single coherent response that follows the user's instructions. Do not mention the parts or the merging process.

Partial analyses:
{combined}

User's instructions: {instructions}"""
        return await _generate(reduce_prompt, model)

    except asyncio.TimeoutError:
        return "Error: The request timed out. Please try again with a more specific question or less content."
    except Exception as e:
        return f"Error analyzing content: {str(e)}. Please make sure Ollama is running and properly configured."

def sync_extract_structured(content, fields, model=None):
    """Extract records with the given fields from content as JSON.
    Returns (records, error) — one of the two is None."""
    model = model or MODEL_NAME
    prompt = f"""Extract structured data from the content below.

Fields to extract for each record: {', '.join(fields)}

Return ONLY a JSON array of objects, each object having exactly these keys: {', '.join(fields)}.
No explanations, no markdown fences, just the JSON array. Return [] if nothing matches.

Content:
{content[:MAX_CONTENT_CHARS]}"""
    try:
        result = asyncio.run(_generate(prompt, model))
    except Exception as e:
        return None, f"Error: {str(e)}"

    # Pull the JSON array out of the response (models often wrap it in prose/fences)
    match = re.search(r'\[.*\]', result, re.DOTALL)
    if not match:
        return None, f"Could not find a JSON array in the model response: {result[:200]}"
    try:
        records = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        return None, f"Model returned invalid JSON: {str(e)}"
    if not isinstance(records, list):
        return None, "Model did not return a JSON array"
    return records, None

def stream_generate(prompt, model=None):
    """Yield Ollama response tokens as they arrive (sync generator for st.write_stream)"""
    import requests
    model = model or MODEL_NAME
    data = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.7,
            "num_predict": 4000,
            "top_p": 0.9,
            "top_k": 40
        }
    }
    with requests.post(OLLAMA_API_URL, json=data, stream=True, timeout=300) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            try:
                part = json.loads(line)
            except json.JSONDecodeError:
                continue
            if 'response' in part:
                yield part['response']
            if part.get('done'):
                break

def sync_extract_pdf_text(pdf_paths):
    """Extract combined text from PDFs (sync), capped for the context window"""
    try:
        texts = asyncio.run(process_pdf_files(pdf_paths))
        combined = ""
        for path, text in zip(pdf_paths, texts):
            if text:
                combined += f"\n--- {os.path.basename(path)} ---\n{text}"
        return combined[:MAX_CONTENT_CHARS]
    except Exception as e:
        logger.error(f"Error extracting PDF text: {str(e)}")
        return ""

def sync_parse_large_content(content, instructions, model=None, progress_callback=None):
    """Synchronous wrapper for parse_large_content"""
    try:
        return asyncio.run(parse_large_content(content, instructions, model, progress_callback))
    except Exception as e:
        logger.error(f"Error in sync_parse_large_content: {str(e)}")
        return f"Error: {str(e)}"

@retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
async def parse_with_ollama(pdf_paths, description, model=None):
    """
    Parse the content using Ollama API based on the provided description.
    Uses async/await for better performance and retry mechanism for reliability.
    """
    logger.info("Starting parse_with_ollama function")
    model = model or MODEL_NAME

    # Check if Ollama is available
    available, message = check_ollama_availability(model)
    if not available:
        logger.error(f"Ollama is not available: {message}")
        return message

    # Extract text from any provided PDFs and include it in the prompt
    pdf_text = ""
    if pdf_paths:
        texts = await process_pdf_files(pdf_paths)
        for path, text in zip(pdf_paths, texts):
            if text:
                pdf_text += f"\n--- {os.path.basename(path)} ---\n{text}"

    # Prepare the prompt for the API
    if pdf_text:
        # Cap length to stay within the model's context window
        pdf_text = pdf_text[:24000]
        prompt = f"""Analyze the following PDF content and provide a response based on the user's instructions.

PDF content:
{pdf_text}

User's instructions: {description}

Provide a clear, well-formatted response that directly addresses the user's request."""
    else:
        prompt = f"""Analyze the following content and provide a response based on the user's instructions:

{description}

Provide a clear, well-formatted response that directly addresses the user's request."""

    logger.info(f"Sending request to Ollama API with model: {model}")
    try:
        return await _generate(prompt, model)
    except asyncio.TimeoutError:
        return "Error: The request timed out. Please try again with a more specific question or less content."
    except Exception as e:
        return f"Error analyzing content: {str(e)}. Please make sure Ollama is running and properly configured."

# Synchronous wrapper for Streamlit compatibility
def sync_parse_with_deepseek(pdf_paths, description, model=None):
    """Synchronous wrapper for async parse function"""
    try:
        logger.info("Starting sync_parse_with_deepseek")
        logger.info(f"Description: {description[:100]}...")  # Log first 100 chars of description
        result = asyncio.run(parse_with_ollama(pdf_paths, description, model))
        logger.info("Successfully completed sync_parse_with_deepseek")
        logger.info(f"Result: {result[:100]}...")  # Log first 100 chars of result
        return result
    except Exception as e:
        logger.error(f"Error in sync_parse_with_deepseek: {str(e)}")
        return f"Error: {str(e)}"

