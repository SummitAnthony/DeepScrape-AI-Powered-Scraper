import json

import cli


class TestParseArgs:
    def test_scrape_subcommand(self):
        args = cli.parse_args(["scrape", "https://x.com"])
        assert args.command == "scrape"
        assert args.url == "https://x.com"

    def test_pdfs_subcommand(self):
        args = cli.parse_args(["pdfs", "https://x.com"])
        assert args.command == "pdfs"

    def test_extract_subcommand_with_fields(self):
        args = cli.parse_args(["extract", "https://x.com", "--fields", "name,price"])
        assert args.command == "extract"
        assert args.fields == "name,price"

    def test_extract_model_option(self):
        args = cli.parse_args(["extract", "https://x.com", "--fields", "a", "--model", "llama3"])
        assert args.model == "llama3"


class TestRunScrape:
    def test_outputs_json(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "scrape_website_content",
                            lambda url: {"title": "T", "paragraphs": ["p1"], "headings": [], "images": [], "links": []})
        code = cli.run(cli.parse_args(["scrape", "https://x.com"]))
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["title"] == "T"


class TestRunPdfs:
    def test_outputs_links(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "scrape_website", lambda url: ["https://x.com/a.pdf"])
        code = cli.run(cli.parse_args(["pdfs", "https://x.com"]))
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["pdf_links"] == ["https://x.com/a.pdf"]


class TestRunExtract:
    def test_outputs_records(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "scrape_website_content",
                            lambda url: {"title": "T", "paragraphs": ["Widget $10"], "headings": [], "images": [], "links": []})
        monkeypatch.setattr(cli, "sync_extract_structured",
                            lambda content, fields, model=None: ([{"name": "Widget"}], None))
        code = cli.run(cli.parse_args(["extract", "https://x.com", "--fields", "name"]))
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["records"] == [{"name": "Widget"}]

    def test_extract_error_nonzero_exit(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "scrape_website_content",
                            lambda url: {"title": "", "paragraphs": [], "headings": [], "images": [], "links": []})
        monkeypatch.setattr(cli, "sync_extract_structured",
                            lambda content, fields, model=None: (None, "no data"))
        code = cli.run(cli.parse_args(["extract", "https://x.com", "--fields", "name"]))
        assert code == 1
        assert "no data" in capsys.readouterr().err

    def test_scrape_failure_nonzero_exit(self, monkeypatch, capsys):
        def boom(url):
            raise RuntimeError("network down")
        monkeypatch.setattr(cli, "scrape_website_content", boom)
        code = cli.run(cli.parse_args(["scrape", "https://x.com"]))
        assert code == 1
        assert "network down" in capsys.readouterr().err
