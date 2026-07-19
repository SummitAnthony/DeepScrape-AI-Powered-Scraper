import scrape

URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/a</loc></url>
  <url><loc>https://example.com/b.pdf</loc></url>
</urlset>"""

SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap1.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap2.xml</loc></sitemap>
</sitemapindex>"""


class TestParseSitemapXml:
    def test_urlset_returns_locs(self):
        urls, sub = scrape.parse_sitemap_xml(URLSET)
        assert urls == ["https://example.com/a", "https://example.com/b.pdf"]
        assert sub == []

    def test_index_returns_sub_sitemaps(self):
        urls, sub = scrape.parse_sitemap_xml(SITEMAP_INDEX)
        assert urls == []
        assert sub == ["https://example.com/sitemap1.xml", "https://example.com/sitemap2.xml"]

    def test_garbage_returns_empty(self):
        urls, sub = scrape.parse_sitemap_xml("not xml at all")
        assert urls == []
        assert sub == []


class TestFetchSitemapUrls:
    def test_follows_index_nesting(self, monkeypatch):
        pages = {
            "https://example.com/sitemap.xml": SITEMAP_INDEX,
            "https://example.com/sitemap1.xml":
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/p1</loc></url></urlset>',
            "https://example.com/sitemap2.xml":
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/p2</loc></url></urlset>',
        }
        monkeypatch.setattr(scrape, "fetch_html", lambda url, timeout=15: pages.get(url))
        urls = scrape.fetch_sitemap_urls("https://example.com/sitemap.xml")
        assert set(urls) == {"https://example.com/p1", "https://example.com/p2"}

    def test_default_location_from_domain(self, monkeypatch):
        seen = []
        monkeypatch.setattr(scrape, "fetch_html",
                            lambda url, timeout=15: seen.append(url) or URLSET)
        urls = scrape.fetch_sitemap_urls("https://example.com/some/deep/page")
        assert seen[0] == "https://example.com/sitemap.xml"
        assert "https://example.com/a" in urls

    def test_max_urls_cap(self, monkeypatch):
        many = "".join(f"<url><loc>https://example.com/{i}</loc></url>" for i in range(100))
        xml = f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{many}</urlset>'
        monkeypatch.setattr(scrape, "fetch_html", lambda url, timeout=15: xml)
        urls = scrape.fetch_sitemap_urls("https://example.com/sitemap.xml", max_urls=10)
        assert len(urls) == 10
