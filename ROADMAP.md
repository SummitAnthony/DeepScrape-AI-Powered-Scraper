# DeepScrape Improvement Roadmap

One item per iteration. Implement minimally, verify, commit, push, check off.

## Queue (priority order)

- [ ] **Cleanup & README**: remove `st.write("Debug: ...")` lines, dedupe the two batch-download blocks, update README + requirements pins.

## Done

- [x] **Caching**: disk cache for pages (URL hash, 1h TTL), verified roundtrip — `688ef91`
- [x] **Deep crawl mode**: same-domain BFS + robots.txt + concurrent downloads — `df75bf6`
- [x] **Structured extraction**: fields → LLM JSON → table + CSV/JSON downloads — `aecc355`
- [x] **Streaming responses**: st.write_stream for content + PDF analysis — `8c8f0d4`
- [x] **Chunked map-reduce analysis**: split → per-chunk analysis with progress → merge; deduped HTTP into _generate — `97bb2ec`
- [x] **Model picker**: sidebar dropdown from Ollama /api/tags, model threaded through all LLM calls — `a2b3ddb`
- [x] **Headless + fast scraping**: requests-first, headless Selenium fallback, no per-image sleep — `c94391a`
- [x] **Wire PDFs into the AI layer**: PDF text extraction feeds Ollama; new Analyze Downloaded PDFs UI — `5e57534`
- [x] **Fix broken Streamlit flow**: session_state-persisted results, working download buttons, llm_prompt key fix — `7b8c10c`
