# DeepScrape Improvement Roadmap

One item per iteration. Implement minimally, verify, commit, push, check off.

## Queue (priority order) — Round 2 (TDD: write tests first, make them pass, then ship)

- [ ] **Test foundation + CI**: pytest suite for existing pure functions (`is_download_link`, `get_absolute_url`, `get_filename_from_url`, cache put/get, `records_to_csv`, `scraped_data_to_text`, structured-extraction JSON parsing) + GitHub Actions workflow running it on push.
- [ ] **RAG chat over PDFs**: chunk downloaded PDF text, embed via Ollama `/api/embeddings`, store vectors in SQLite, retrieve top-k relevant chunks for a question, answer with source citations. Chat-style multi-turn UI. TDD: chunking/similarity/store tests first.
- [ ] **Playwright migration**: replace Selenium + chromedriver.exe dance with Playwright (auto-managed browsers). Keep requests-first + cache pipeline. TDD: pipeline fallback logic tests with mocked fetchers.
- [ ] **Smart crawl**: LLM ranks candidate links by relevance to the user's stated goal before following; goal input in UI. TDD: link-ranking prompt parsing + queue-priority tests.
- [ ] **Watch mode**: monitor a URL on interval, diff text content between runs, show what changed. TDD: diff/normalize tests first.

## Done

- [x] **Cleanup & README**: debug lines removed, README covers all new features, pymupdf added — `ac64dfc`

- [x] **Caching**: disk cache for pages (URL hash, 1h TTL), verified roundtrip — `688ef91`
- [x] **Deep crawl mode**: same-domain BFS + robots.txt + concurrent downloads — `df75bf6`
- [x] **Structured extraction**: fields → LLM JSON → table + CSV/JSON downloads — `aecc355`
- [x] **Streaming responses**: st.write_stream for content + PDF analysis — `8c8f0d4`
- [x] **Chunked map-reduce analysis**: split → per-chunk analysis with progress → merge; deduped HTTP into _generate — `97bb2ec`
- [x] **Model picker**: sidebar dropdown from Ollama /api/tags, model threaded through all LLM calls — `a2b3ddb`
- [x] **Headless + fast scraping**: requests-first, headless Selenium fallback, no per-image sleep — `c94391a`
- [x] **Wire PDFs into the AI layer**: PDF text extraction feeds Ollama; new Analyze Downloaded PDFs UI — `5e57534`
- [x] **Fix broken Streamlit flow**: session_state-persisted results, working download buttons, llm_prompt key fix — `7b8c10c`
