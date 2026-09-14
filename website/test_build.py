"""Offline publishing checks: page structure, links, escaping, and content coverage."""
import copy
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

import build


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []
        self.headings = 0
        self.main = 0
        self.descriptions = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if tag == "h1":
            self.headings += 1
        if tag == "main":
            self.main += 1
        if tag == "meta" and attrs.get("name") == "description":
            self.descriptions += 1


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name) / "AgentVerse"
        build.build(cls.output)
        cls.entries = build.load_catalog()
        cls.stories = build.load_stories(cls.entries)
        cls.pages = {}
        for path in cls.output.rglob("*.html"):
            parser = PageParser()
            parser.feed(path.read_text(encoding="utf-8"))
            cls.pages[path.resolve()] = parser

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_every_manifest_has_a_static_page(self):
        self.assertEqual(len(self.pages), len(self.entries) + 5)
        for entry in self.entries:
            path = self.output / "scenarios" / f'{entry["name"]}.html'
            self.assertTrue(path.is_file(), entry["name"])
            html = path.read_text(encoding="utf-8")
            self.assertIn(build.text(self.stories[entry["name"]]["reality"]), html)
            self.assertIn("What&rsquo;s real. What&rsquo;s simulated.", html)
            self.assertIn("Costs:", html)
        self.assertTrue((self.output / ".nojekyll").is_file())

    def test_accessible_page_structure(self):
        for path, parser in self.pages.items():
            with self.subTest(page=path.name):
                self.assertEqual(parser.headings, 1)
                self.assertEqual(parser.main, 1)
                self.assertEqual(parser.descriptions, 1)
                self.assertEqual(len(parser.ids), len(set(parser.ids)))
                self.assertIn("main", parser.ids)
                html = path.read_text(encoding="utf-8")
                self.assertIn('<html lang="en">', html)
                self.assertIn("Skip to content", html)
                self.assertIn("--cp-bg:", html)
                self.assertIn("prefers-reduced-motion", html)

    def test_links_work_at_project_subpath(self):
        for path, parser in self.pages.items():
            for href in parser.links:
                with self.subTest(page=path.name, href=href):
                    link = urlsplit(href)
                    self.assertNotEqual(link.scheme, "javascript")
                    if link.scheme:
                        self.assertEqual(link.scheme, "https")
                        self.assertTrue(link.netloc)
                        continue
                    self.assertFalse(href.startswith("/"), "Root-relative links break project Pages.")
                    target = (path.parent / unquote(link.path)).resolve() if link.path else path
                    self.assertTrue(target.is_relative_to(self.output.resolve()))
                    self.assertTrue(target.is_file())
                    if link.fragment:
                        self.assertIn(link.fragment, self.pages[target].ids)

    def test_github_source_paths_exist(self):
        for path, parser in self.pages.items():
            for href in parser.links:
                for prefix in (build.SOURCE, f"{build.REPO}/blob/main/"):
                    if href.startswith(prefix):
                        relative = unquote(href.removeprefix(prefix).split("#")[0])
                        self.assertTrue((build.ROOT / relative).exists(), f"{path.name}: {href}")

    def test_static_content_works_without_javascript(self):
        html = (self.output / "explore.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('class="scenario-card"'), len(self.entries))
        self.assertIn("<noscript>", html)
        for entry in self.entries:
            self.assertIn(f'scenarios/{entry["name"]}.html', html)

    def test_hero_slider_covers_every_demo(self):
        html = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('class="hero-slide"'), len(self.entries))
        self.assertEqual(html.count('class="slide-dot"'), len(self.entries))
        self.assertIn('aria-roledescription="carousel"', html)
        self.assertIn('aria-label="Next scenario"', html)
        self.assertIn('aria-label="Previous scenario"', html)
        for entry in self.entries:
            self.assertIn(f'aria-label="Show {build.text(entry["title"])}"', html)

    def test_audience_and_purpose_sections(self):
        html = (self.output / "about.html").read_text(encoding="utf-8")
        self.assertIn('id="who-is-this-for"', html)
        self.assertIn('id="why-agentverse"', html)
        self.assertIn("Who is AgentVerse for?", html)
        self.assertEqual(html.count('class="audience-card"'), 4)
        self.assertIn("collaboration across", html)
        self.assertIn("not finished products", html)
        start = (self.output / "get-started.html").read_text(encoding="utf-8")
        self.assertIn('href="about.html#who-is-this-for"', start)
        for path in self.pages:
            content = path.read_text(encoding="utf-8")
            prefix = "../" if path.parent.name == "scenarios" else "./"
            self.assertIn(f'href="{prefix}about.html"', content)
        self.assertIn('href="./about.html" aria-current="page"', html)

    def test_metadata_is_escaped(self):
        entry = copy.deepcopy(self.entries[0])
        story = copy.deepcopy(self.stories[entry["name"]])
        story["headline"] = '<img src=x onerror="alert(1)">'
        story["summary"] = 'A "quoted" & unsafe <script> example'
        rendered = build.card(entry, story)
        self.assertNotIn("<img", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;img", rendered)
        self.assertIn("&quot;", rendered)

    def test_source_link_encoding(self):
        self.assertEqual(
            build.source_link("src/example/README.md#quick-start"),
            build.SOURCE + "src/example/README.md#quick-start",
        )

    def test_missing_editorial_copy_fails_explicitly(self):
        entries = self.entries + [{"name": "new-demo"}]
        with self.assertRaisesRegex(ValueError, "Missing:"):
            build.load_stories(entries)

    def test_invalid_quickstart_fails_explicitly(self):
        stories = copy.deepcopy(self.stories)
        stories[self.entries[0]["name"]]["start_path"] = "../outside.md"
        with patch.object(build.json, "loads", return_value=stories):
            with self.assertRaisesRegex(ValueError, "existing source document"):
                build.load_stories(self.entries)

    def test_invalid_copy_fails_explicitly(self):
        stories = copy.deepcopy(self.stories)
        stories[self.entries[0]["name"]]["steps"] = []
        with patch.object(build.json, "loads", return_value=stories):
            with self.assertRaisesRegex(ValueError, "steps must be"):
                build.load_stories(self.entries)


if __name__ == "__main__":
    unittest.main()
