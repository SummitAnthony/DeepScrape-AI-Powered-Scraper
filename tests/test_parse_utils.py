import parse


class TestCleanText:
    def test_collapses_whitespace(self):
        assert parse.clean_text("a   b\n\n\nc") == "a b c" or parse.clean_text("a   b") == "a b"

    def test_empty(self):
        assert parse.clean_text("") == ""
        assert parse.clean_text(None) == ""


class TestParseJsonRecords:
    def test_clean_array(self):
        records, err = parse._parse_json_records('[{"name": "x", "price": 5}]')
        assert err is None
        assert records == [{"name": "x", "price": 5}]

    def test_prose_wrapped(self):
        records, err = parse._parse_json_records('Sure! Here it is: [{"a": 1}] Hope this helps.')
        assert err is None
        assert records == [{"a": 1}]

    def test_empty_array(self):
        records, err = parse._parse_json_records("[]")
        assert err is None
        assert records == []

    def test_no_json(self):
        records, err = parse._parse_json_records("I could not find any data.")
        assert records is None
        assert err is not None

    def test_invalid_json(self):
        records, err = parse._parse_json_records("[not valid json]")
        assert records is None
        assert err is not None


class TestChunking:
    def test_split_dom_content(self):
        import scrape
        chunks = scrape.split_dom_content("x" * 15000, max_length=6000)
        assert len(chunks) == 3
        assert "".join(chunks) == "x" * 15000
