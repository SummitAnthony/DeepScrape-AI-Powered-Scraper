# DeepScrape Improvement Roadmap

One item per iteration. Implement minimally, verify, commit, push, check off.

## Queue (priority order)

- [ ] **Fix broken Streamlit flow**: nested `st.button` inside `if st.button("Start Scraping")` never fires (Streamlit reruns wipe the outer condition). Restructure with session_state so PDF results + download buttons persist across reruns. Also fix `llm_prompt` widget key/value conflict.
- [ ] **Wire PDFs into the AI layer**: `parse_with_ollama(pdf_paths, ...)` ignores `pdf_paths` — extract PDF text (already have `extract_text_from_pdf`) and feed it into the prompt. Add a "Analyze Downloaded PDFs" section in the UI.
- [ ] **Headless + fast scraping**: enable `--headless=new`, try plain `requests` first and only fall back to Selenium when the page needs JS. Remove per-image `rate_limit()` sleep (it's metadata, not a request). Remove noisy per-link logging.
- [ ] **Model picker**: sidebar dropdown populated from Ollama `/api/tags`; replace hardcoded `llama2`. Persist selection in session_state.
- [ ] **Chunked map-reduce analysis**: for content larger than the context window, split (reuse `split_dom_content`), summarize chunks, then combine. Show progress.
- [ ] **Streaming responses**: stream Ollama output into the UI (`st.write_stream`) instead of blocking for minutes.
- [ ] **Structured extraction**: user provides fields (e.g. "name, price, date") → prompt LLM to return JSON → render table + CSV/JSON download buttons.
- [ ] **Deep crawl mode**: follow same-domain links to depth N (default 1), respect robots.txt, dedupe URLs, aggregate PDFs/content across pages. Concurrent downloads via ThreadPoolExecutor.
- [ ] **Caching**: cache scraped pages (URL hash → disk, TTL) so re-analysis doesn't re-scrape.
- [ ] **Cleanup & README**: remove `st.write("Debug: ...")` lines, dedupe the two batch-download blocks, update README + requirements pins.

## Done

(move checked items here with commit hash)
