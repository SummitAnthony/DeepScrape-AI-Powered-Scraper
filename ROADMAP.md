# DeepScrape Improvement Roadmap

One item per iteration. Implement minimally, verify, commit, push, check off.

## Queue (priority order)

(empty — rounds 1 and 2 fully shipped)

## Done

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
