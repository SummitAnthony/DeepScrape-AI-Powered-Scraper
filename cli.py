"""Command-line interface for DeepScrape — drive the pipeline from the terminal.

Examples:
  python cli.py scrape https://example.com
  python cli.py pdfs https://example.com
  python cli.py extract https://example.com --fields "name,price,date"
"""
import argparse
import json
import sys

from scrape import scrape_website, scrape_website_content
from parse import sync_extract_structured


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="deepscrape", description="AI-powered web scraper (CLI)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scrape = sub.add_parser("scrape", help="Scrape a page's structured content as JSON")
    p_scrape.add_argument("url")

    p_pdfs = sub.add_parser("pdfs", help="List downloadable document links on a page")
    p_pdfs.add_argument("url")

    p_extract = sub.add_parser("extract", help="Extract structured records (given fields) as JSON")
    p_extract.add_argument("url")
    p_extract.add_argument("--fields", required=True, help="Comma-separated field names")
    p_extract.add_argument("--model", default=None, help="Ollama model to use")

    return parser.parse_args(argv)


def run(args):
    """Execute a parsed command. Returns a process exit code (0 ok, 1 error)."""
    try:
        if args.command == "scrape":
            print(json.dumps(scrape_website_content(args.url), indent=2, ensure_ascii=False))
            return 0
        if args.command == "pdfs":
            print(json.dumps({"pdf_links": scrape_website(args.url)}, indent=2, ensure_ascii=False))
            return 0
        if args.command == "extract":
            fields = [f.strip() for f in args.fields.split(",") if f.strip()]
            content = scrape_website_content(args.url)
            text = f"{content.get('title', '')}\n" + "\n".join(content.get("paragraphs", []))
            records, error = sync_extract_structured(text, fields, args.model)
            if error:
                print(error, file=sys.stderr)
                return 1
            print(json.dumps({"records": records}, indent=2, ensure_ascii=False))
            return 0
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1
    return 1


def main():
    sys.exit(run(parse_args()))


if __name__ == "__main__":
    main()
