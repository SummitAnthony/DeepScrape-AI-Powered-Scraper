import rag


class TestChunkText:
    def test_empty(self):
        assert rag.chunk_text("") == []

    def test_short_text_single_chunk(self):
        assert rag.chunk_text("hello world", chunk_size=1000, overlap=100) == ["hello world"]

    def test_overlap(self):
        text = "x" * 2000
        chunks = rag.chunk_text(text, chunk_size=1000, overlap=200)
        assert len(chunks) == 3  # starts at 0, 800, 1600
        assert chunks[0][-200:] == chunks[1][:200]

    def test_covers_full_text(self):
        text = "abcdefghij" * 300  # 3000 chars
        chunks = rag.chunk_text(text, chunk_size=1000, overlap=100)
        assert chunks[0] == text[:1000]
        assert chunks[-1][-1] == text[-1]


class TestCosineSimilarity:
    def test_identical(self):
        assert abs(rag.cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) - 1.0) < 1e-9

    def test_orthogonal(self):
        assert abs(rag.cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-9

    def test_zero_vector(self):
        assert rag.cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0


class TestRagStore:
    def test_add_and_top_k(self, tmp_path):
        db = str(tmp_path / "test.db")
        store = rag.RagStore(db)
        store.add_document("a.pdf", ["about cats", "about dogs"], [[1.0, 0.0], [0.8, 0.2]])
        store.add_document("b.pdf", ["about planes"], [[0.0, 1.0]])
        results = store.top_k([1.0, 0.0], k=2)
        store.close()
        assert len(results) == 2
        assert results[0][0] == "a.pdf"
        assert results[0][1] == "about cats"
        assert results[0][2] >= results[1][2]  # sorted by score desc

    def test_reindex_replaces_document(self, tmp_path):
        db = str(tmp_path / "test.db")
        store = rag.RagStore(db)
        store.add_document("a.pdf", ["old"], [[1.0, 0.0]])
        store.add_document("a.pdf", ["new"], [[1.0, 0.0]])
        results = store.top_k([1.0, 0.0], k=10)
        store.close()
        assert len(results) == 1
        assert results[0][1] == "new"

    def test_persistence(self, tmp_path):
        db = str(tmp_path / "test.db")
        store = rag.RagStore(db)
        store.add_document("a.pdf", ["persisted"], [[1.0]])
        store.close()
        store2 = rag.RagStore(db)
        assert store2.has_document("a.pdf")
        assert not store2.has_document("missing.pdf")
        store2.close()


class TestBuildRagPrompt:
    def test_includes_sources_and_question(self):
        retrieved = [("a.pdf", "cats are great", 0.9), ("b.pdf", "dogs are loyal", 0.8)]
        prompt = rag.build_rag_prompt("What about cats?", retrieved)
        assert "a.pdf" in prompt
        assert "cats are great" in prompt
        assert "What about cats?" in prompt

    def test_includes_history(self):
        prompt = rag.build_rag_prompt(
            "And dogs?",
            [("a.pdf", "text", 0.5)],
            history=[{"role": "user", "content": "What about cats?"},
                     {"role": "assistant", "content": "Cats are great."}]
        )
        assert "What about cats?" in prompt
        assert "Cats are great." in prompt
