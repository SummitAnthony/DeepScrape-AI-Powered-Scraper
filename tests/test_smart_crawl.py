import scrape


class TestExtractCandidateLinks:
    HTML = """
    <html><body>
      <a href="/reports">Annual Reports</a>
      <a href="/reports#section">Reports anchor dupe</a>
      <a href="https://other.com/x">External</a>
      <a href="/about">About us</a>
    </body></html>
    """

    def test_same_domain_only_and_dedupe(self):
        candidates = scrape.extract_candidate_links(self.HTML, "https://example.com/", "example.com")
        urls = [u for u, _ in candidates]
        assert "https://example.com/reports" in urls
        assert "https://example.com/about" in urls
        assert not any("other.com" in u for u in urls)
        assert len(urls) == len(set(urls))  # fragment dupe collapsed

    def test_includes_link_text(self):
        candidates = scrape.extract_candidate_links(self.HTML, "https://example.com/", "example.com")
        by_url = dict(candidates)
        assert by_url["https://example.com/reports"] == "Annual Reports"


class TestParseRankedIndices:
    def test_clean_array(self):
        assert scrape.parse_ranked_indices("[2, 0, 1]", 3) == [2, 0, 1]

    def test_prose_wrapped(self):
        assert scrape.parse_ranked_indices("Best links: [1, 2] hope that helps", 3) == [1, 2]

    def test_out_of_range_filtered(self):
        assert scrape.parse_ranked_indices("[0, 5, 1]", 2) == [0, 1]

    def test_duplicates_removed(self):
        assert scrape.parse_ranked_indices("[1, 1, 0]", 2) == [1, 0]

    def test_garbage(self):
        assert scrape.parse_ranked_indices("no list here", 3) == []

    def test_empty(self):
        assert scrape.parse_ranked_indices("[]", 3) == []


class TestSmartCrawl:
    SITE = {
        "https://example.com/": """
            <a href="/good">2024 exam papers</a>
            <a href="/bad">Privacy policy</a>
            <a href="/a.pdf">paper A</a>
        """,
        "https://example.com/good": '<a href="/b.pdf">paper B</a>',
        "https://example.com/bad": '<a href="/c.pdf">unrelated C</a>',
    }

    def _setup(self, monkeypatch):
        monkeypatch.setattr(scrape, "get_page_html", lambda url, **kw: self.SITE[url])
        monkeypatch.setattr(scrape, "is_allowed_by_robots", lambda url, ua='*': True)
        monkeypatch.setattr(scrape, "rate_limit", lambda: None)

    def test_follows_only_ranked_links(self, monkeypatch):
        self._setup(monkeypatch)
        ranked_calls = []

        def fake_ranker(goal, candidates):
            ranked_calls.append((goal, candidates))
            # pick only the /good link
            return [i for i, (u, t) in enumerate(candidates) if u.endswith("/good")]

        result = scrape.smart_crawl("https://example.com/", "find 2024 exam papers",
                                    max_depth=1, ranker=fake_ranker)
        assert "https://example.com/good" in result["pages"]
        assert "https://example.com/bad" not in result["pages"]
        assert "https://example.com/a.pdf" in result["pdf_links"]
        assert "https://example.com/b.pdf" in result["pdf_links"]
        assert "https://example.com/c.pdf" not in result["pdf_links"]
        assert ranked_calls[0][0] == "find 2024 exam papers"

    def test_depth_zero_no_ranking(self, monkeypatch):
        self._setup(monkeypatch)

        def exploding_ranker(goal, candidates):
            raise AssertionError("ranker should not be called at depth 0")

        result = scrape.smart_crawl("https://example.com/", "goal", max_depth=0, ranker=exploding_ranker)
        assert result["pages"] == ["https://example.com/"]
        assert "https://example.com/a.pdf" in result["pdf_links"]
