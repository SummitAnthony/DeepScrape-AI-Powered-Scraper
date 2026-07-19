# DeepScrape — AI-Powered Scraper & Analyzer

A powerful web application that combines fast web scraping, site crawling, and local-AI analysis (Ollama) to extract, download, and understand web content and PDF documents.

How to - https://www.youtube.com/watch?v=plZyfU9T70Q

## How It Works

Every page fetch goes through a three-tier pipeline:

1. **Disk cache** — pages already scraped in the last hour are served instantly
2. **Plain requests** — fast path, no browser needed for static pages
3. **Headless Chrome (Selenium)** — automatic fallback for JavaScript-heavy pages

AI features run fully locally through [Ollama](https://ollama.ai/) — no API keys, no data leaves your machine.

## System Requirements

- Python 3.8 or higher
- Windows 10/11 (64-bit)
- Google Chrome (any recent version — only needed for JS-heavy pages; the included downloader fetches the matching ChromeDriver automatically)
- [Ollama](https://ollama.ai/) with at least one model pulled (for AI features)

## Features

- **Fast Scraping**: Plain-requests fetching with automatic headless-Chrome fallback for JS-heavy pages
- **Deep Crawl**: Follow same-domain links up to depth 3 (respects robots.txt) to find PDFs across a whole site
- **PDF Scraping**: Automatically finds and downloads PDF files from websites
- **Concurrent Batch Download**: Download multiple PDFs in parallel with progress tracking
- **AI Analysis**: Ask anything about scraped content or downloaded PDFs (requires Ollama)
  - Streaming responses render live as they're generated
  - Large content is automatically chunked and analyzed map-reduce style
  - Pick any locally installed Ollama model from the sidebar
- **Structured Extraction**: Give a list of fields (e.g. `name, price, date`) and get a table with CSV/JSON export
- **Page Caching**: Scraped pages are cached on disk (1h TTL) so re-analysis is instant
- **Custom Download Location**: Choose where to save downloaded files

## Local Installation

### 1. Prerequisites

#### Chrome Installation
- Install any recent version of Google Chrome (64-bit). Chrome is only used as a fallback for JavaScript-heavy pages — most scraping runs without it.

#### ChromeDriver Setup
The application includes an automatic ChromeDriver downloader (`download_chromedriver.py`) that will:
- Detect your Chrome version
- Download the matching ChromeDriver version
- Install it in the correct location

### 2. Installation Steps

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

4. Download and setup ChromeDriver:
```bash
python download_chromedriver.py
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

### Chrome/ChromeDriver Version Mismatch
If you encounter version mismatch errors:
1. Check your Chrome version (Help > About Google Chrome)
2. Run `python download_chromedriver.py` to download the matching ChromeDriver version
3. Ensure ChromeDriver is in your PATH or in the project directory

### Common Issues
1. **ChromeDriver not found**: Run `python download_chromedriver.py`
2. **Version mismatch**: Make sure Chrome and ChromeDriver versions match
3. **Permission errors**: Run as administrator if needed
4. **Antivirus blocking**: Add exceptions for ChromeDriver

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
├── main.py                   # Streamlit UI: scraping, downloads, AI analysis, extraction
├── scrape.py                 # Fetch pipeline (cache/requests/Selenium), crawler, PDF downloads
├── parse.py                  # Ollama integration: streaming, map-reduce, structured extraction
├── download_chromedriver.py  # Auto-downloads ChromeDriver matching your Chrome version
├── setup.bat                 # Windows one-shot setup helper
├── requirements.txt          # Python dependencies
├── ROADMAP.md                # Improvement log (what shipped, what's next)
├── README.md                 # Project documentation
└── .gitignore                # Ignores downloads/, outputs/, .page_cache/, etc.
```

At runtime the app also creates `downloads/` (saved PDFs), `outputs/` (exports), and `.page_cache/` (scraped-page cache, 1h TTL) — all gitignored.

## Dependencies

See `requirements.txt` for the full pinned list. Key packages: streamlit, selenium, beautifulsoup4, requests, aiohttp, PyPDF2, pymupdf, fpdf, retrying, webdriver_manager.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Ollama](https://ollama.ai/) for AI capabilities
- [Selenium](https://www.selenium.dev/) for web scraping
- [Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/) for ChromeDriver
