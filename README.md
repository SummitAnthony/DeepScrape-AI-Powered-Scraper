# DeepScrape — AI-Powered Scraper & Analyzer

A powerful web application that combines fast web scraping, site crawling, and local-AI analysis (Ollama) to extract, download, and understand web content and PDF documents.

How to - https://www.youtube.com/watch?v=plZyfU9T70Q

## How It Works

Every page fetch goes through a four-tier pipeline:

1. **Disk cache** — pages already scraped in the last hour are served instantly
2. **Plain requests** — fast path, no browser needed for static pages
3. **TLS impersonation (curl_cffi)** — mimics a real Chrome TLS fingerprint to get past anti-bot blocks, with optional proxy rotation
4. **Headless Chromium (Playwright)** — final fallback for JavaScript-heavy pages

AI features run fully locally through [Ollama](https://ollama.ai/) — no API keys, no data leaves your machine.

## System Requirements

- Python 3.8 or higher
- Windows 10/11 (64-bit), macOS, or Linux
- [Ollama](https://ollama.ai/) with at least one model pulled (for AI features)

No separate Chrome/ChromeDriver install needed — Playwright manages its own headless Chromium.

## Features

- **Fast Scraping**: Four-tier fetch pipeline (cache → requests → TLS impersonation → headless browser)
- **Anti-Bot Resilience**: curl_cffi TLS fingerprint impersonation gets past common bot blocks; add a `proxies.txt` (one proxy per line) to rotate proxies per request
- **Deep Crawl**: Follow same-domain links up to depth 3 (respects robots.txt) to find PDFs across a whole site
- **Sitemap Ingestion**: Instantly discover every URL on a site by reading its `sitemap.xml` (handles nested sitemap indexes) — no crawling required
- **Multi-Format Harvesting**: Finds and downloads PDF, DOCX, XLSX, and CSV files — all extractable for AI analysis and RAG chat
- **Concurrent Batch Download**: Download multiple PDFs in parallel with progress tracking
- **AI Analysis**: Ask anything about scraped content or downloaded PDFs (requires Ollama)
  - Streaming responses render live as they're generated
  - Large content is automatically chunked and analyzed map-reduce style
  - Pick any locally installed Ollama model from the sidebar
- **Visual Analysis**: Screenshot a full page and analyze it with a vision model (llava) — reads charts, images, and layout that text scraping misses
- **Structured Extraction**: Give a list of fields (e.g. `name, price, date`) and get a table with CSV/JSON export
- **Scrape History**: Every job (URL, mode, items found, time) is logged to SQLite and shown in a sidebar panel with one-click re-run
- **Page Caching**: Scraped pages are cached on disk (1h TTL) so re-analysis is instant
- **REST API**: A FastAPI server (`api.py`) exposes `/scrape`, `/pdfs`, and `/extract` so scripts and other tools can use the pipeline programmatically — run `uvicorn api:app` and see `/docs`
- **Custom Download Location**: Choose where to save downloaded files

## Local Installation

### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/SummitAnthony/DeepScrape-AI-Powered-Scraper.git
cd DeepScrape-AI-Powered-Scraper
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Install the headless browser (used only for JavaScript-heavy pages):
```bash
playwright install chromium
```

5. Install Ollama (for AI features):
- Download and install from [Ollama's website](https://ollama.ai/)
- Pull at least one model (you can switch between installed models from the app's sidebar):
```bash
ollama pull llama3
```

6. Run the application:
```bash
streamlit run main.py
```

## Troubleshooting

1. **"Executable doesn't exist" / browser errors**: Run `playwright install chromium`
2. **AI features not working**: Make sure Ollama is running (`ollama serve`) and a model is pulled
3. **RAG chat indexing fails**: Pull the embedding model — `ollama pull nomic-embed-text`
4. **Permission errors**: Run as administrator if needed

## Usage

1. Open the application (locally)
2. Choose your scraping mode:
   - **Scrape Website**: Extract and analyze website content
   - **Scrape for PDF**: Find and download PDF files

3. Enter a website URL and click "Start Scraping"

4. For PDF scraping:
   - Optionally set a crawl depth to also scan linked pages on the same domain
   - View the list of found PDFs
   - Choose to download all PDFs (concurrent) or individual files
   - Select your preferred download location
   - Use "Analyze Downloaded PDFs" to ask the AI about their contents

5. For website content:
   - Process the content with free-form instructions (streams live)
   - Or use "Structured Extraction" to pull specific fields into a downloadable table

## Project Structure

```
DeepScrape-AI-Powered-Scraper/
├── main.py                   # Streamlit UI: scraping, downloads, AI analysis, extraction, RAG chat
├── scrape.py                 # Fetch pipeline (cache/requests/Playwright), crawler, PDF downloads
├── parse.py                  # Ollama integration: streaming, map-reduce, structured extraction
├── rag.py                    # RAG: chunking, embeddings, SQLite vector store, cited answers
├── watch.py                  # Watch mode: page snapshots + change diffing
├── history.py                # Scrape-history job log (SQLite)
├── api.py                    # FastAPI server: /scrape, /pdfs, /extract endpoints
├── tests/                    # pytest suite (run: python -m pytest -q)
├── setup.bat                 # Windows one-shot setup helper
├── requirements.txt          # Python dependencies
├── ROADMAP.md                # Improvement log (what shipped, what's next)
├── README.md                 # Project documentation
└── .gitignore                # Ignores downloads/, outputs/, .page_cache/, etc.
```

At runtime the app also creates `downloads/` (saved PDFs), `outputs/` (exports), and `.page_cache/` (scraped-page cache, 1h TTL) — all gitignored.

## Dependencies

See `requirements.txt` for the full pinned list. Key packages: streamlit, playwright, beautifulsoup4, requests, aiohttp, PyPDF2, pymupdf, fpdf, retrying.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Ollama](https://ollama.ai/) for AI capabilities
- [Playwright](https://playwright.dev/) for headless browser automation
