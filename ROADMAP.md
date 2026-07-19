# DeepScrape Improvement Roadmap

One item per iteration. Implement minimally, verify, commit, push, check off.

## Queue (priority order) — Round 5: automation & integrations (TDD + update README Features every iteration)

- [ ] **Webhook notifications**: on a detected change, POST a formatted message to a Slack/Discord/generic webhook (`format_change_message` + `notify_webhook`); wire into the watch runner. TDD: message formatting + POST payload tests with a mocked poster.
- [ ] **CLI mode**: `cli.py` with argparse subcommands (`scrape`, `pdfs`, `extract`) reusing the pipeline, printing JSON. TDD: argument parsing + command dispatch tests.

## Done

- [x] **Scheduled watch runner**: cron-friendly batch checker with on_change hook (5 tests) — `78c45ba`
- [x] **Authenticated scraping**: cookies.json injected across all fetch tiers (6 tests) — `39b5f84`
- [x] **Tournament extraction**: 3× extraction + majority-vote merge (8 tests) — `7129a57`

- [x] **Multi-turn conversation memory**: budget-trimmed Conversation in PDF chat (8 tests) — `1c47885`
- [x] **Vision analysis**: full-page screenshot → llava via Ollama (6 tests) — `16c4fb3`
- [x] **API mode**: FastAPI /scrape, /pdfs, /extract endpoints (6 tests) — `f3e44c8`

- [x] **Scrape-history dashboard**: SQLite job log + sidebar re-run (5 tests) — `41cff69`
- [x] **More file types**: DOCX/XLSX/CSV harvest + extraction, fed to AI/RAG (15 tests) — `c761e21`
- [x] **Sitemap ingestion**: sitemap.xml + nested-index parsing, whole-site URL discovery (6 tests) — `d0dfc3a`
- [x] **Anti-bot resilience**: curl_cffi TLS impersonation tier + proxy rotation (7 tests) — `22a3d81`
- [x] **Watch mode**: SQLite snapshots + line diffs + Watch Page UI (11 tests) — `dbd553c`

- [x] **Smart crawl**: goal-directed link ranking via LLM (10 tests) — `9695f8c`
- [x] **Playwright migration**: Selenium fully removed, live fetch verified (6 tests) — `3da8eb9`
- [x] **RAG chat over PDFs**: SQLite vector store + Ollama embeddings + cited streaming chat (12 tests) — `c70ffab`
- [x] **Test foundation + CI**: 25 pytest tests (red→green) + GitHub Actions on push — `bff173f`
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
