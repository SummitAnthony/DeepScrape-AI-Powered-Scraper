import scrape
import parse


class TestClassifyDownloadLink:
    def test_pdf(self):
        assert scrape.classify_download_link("https://x.com/a.pdf") == "pdf"

    def test_docx(self):
        assert scrape.classify_download_link("https://x.com/report.docx") == "docx"

    def test_xlsx(self):
        assert scrape.classify_download_link("https://x.com/data.xlsx") == "xlsx"

    def test_csv(self):
        assert scrape.classify_download_link("https://x.com/export.csv") == "csv"

    def test_query_string_ignored(self):
        assert scrape.classify_download_link("https://x.com/data.csv?token=abc") == "csv"

    def test_non_document(self):
        assert scrape.classify_download_link("https://x.com/index.html") is None

    def test_none(self):
        assert scrape.classify_download_link(None) is None


class TestIsDownloadLinkExtended:
    def test_still_matches_pdf(self):
        assert scrape.is_download_link("https://x.com/a.pdf")

    def test_now_matches_docx(self):
        assert scrape.is_download_link("https://x.com/a.docx")

    def test_now_matches_xlsx_and_csv(self):
        assert scrape.is_download_link("https://x.com/a.xlsx")
        assert scrape.is_download_link("https://x.com/a.csv")

    def test_rejects_plain_page(self):
        assert not scrape.is_download_link("https://x.com/about")


class TestExtractCsvText:
    def test_reads_rows(self, tmp_path):
        p = tmp_path / "d.csv"
        p.write_text("name,price\nWidget,10\nGadget,20\n", encoding="utf-8")
        text = parse.extract_text_from_file(str(p))
        assert "name" in text and "Widget" in text and "20" in text


class TestExtractTextFromFileDispatch:
    def test_csv_dispatch(self, tmp_path):
        p = tmp_path / "d.csv"
        p.write_text("a,b\n1,2\n", encoding="utf-8")
        assert "1" in parse.extract_text_from_file(str(p))

    def test_unknown_extension_returns_empty(self, tmp_path):
        p = tmp_path / "d.xyz"
        p.write_text("stuff", encoding="utf-8")
        assert parse.extract_text_from_file(str(p)) == ""

    def test_missing_file(self):
        assert parse.extract_text_from_file("nope.csv") == ""
