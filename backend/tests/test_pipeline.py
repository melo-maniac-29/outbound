import asyncio
import os
import sys
import unittest
import types
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from nodes.crawl import discover_internal_candidates, discover_sitemap_candidates
from nodes.linkedin_lookup import linkedin_lookup_node
from nodes.profile import build_profile_node


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code


class FakeTavilyClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, search_depth: str = "basic", max_results: int = 5):
        return {
            "results": [
                {
                    "url": "https://www.linkedin.com/company/eallisto/",
                    "title": "Eallisto - Company",
                    "content": "Company profile page",
                },
                {
                    "url": "https://www.linkedin.com/in/shahad-bangla/",
                    "title": "Shahad Bangla | LinkedIn",
                    "content": "Founder at Eallisto",
                },
            ]
        }


class PipelineTests(unittest.TestCase):
    def test_discover_sitemap_candidates_uses_robots_and_sitemap(self):
        def fake_get(url, timeout=8, headers=None):
            if url.endswith("/robots.txt"):
                return FakeResponse("User-agent: *\nSitemap: https://example.com/sitemap.xml\n")
            if url.endswith("/sitemap.xml"):
                return FakeResponse(
                    """<?xml version="1.0" encoding="UTF-8"?>
                    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                        <url><loc>https://example.com/about</loc></url>
                        <url><loc>https://example.com/team</loc></url>
                        <url><loc>https://external.example.org/ignore</loc></url>
                    </urlset>
                    """
                )
            return FakeResponse("", status_code=404)

        with patch("nodes.crawl.requests.get", side_effect=fake_get):
            candidates = discover_sitemap_candidates("https://example.com", limit=10)

        self.assertIn("https://example.com/about", candidates)
        self.assertIn("https://example.com/team", candidates)
        self.assertNotIn("https://external.example.org/ignore", candidates)

    def test_discover_internal_candidates_only_keeps_same_domain_links(self):
        markdown = """
        [About](https://example.com/about)
        [Team](/team)
        [Blog](https://example.com/blog/post)
        [External](https://other.example.org/page)
        """

        candidates = discover_internal_candidates(markdown, "https://example.com")

        urls = [item[0] for item in candidates]
        self.assertIn("https://example.com/about", urls)
        self.assertIn("https://example.com/team", urls)
        self.assertNotIn("https://other.example.org/page", urls)

    def test_build_profile_fallback_uses_context(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "dummy"}, clear=False):
            profile = asyncio.run(
                build_profile_node(
                    markdown_content="",
                    company_name="Eallisto",
                    domain="eallisto.com",
                    founder_name="Shahad Bangla",
                    founder_linkedin="https://www.linkedin.com/in/shahad-bangla/",
                    services=["AI outreach"],
                    signals=["recent growth"],
                    email="faiz@eallisto.com",
                )
            )

        self.assertIn("Eallisto", profile["summary"])
        self.assertIn("Shahad Bangla", profile["summary"])
        self.assertEqual(profile["key_services"], ["AI outreach"])
        self.assertEqual(profile["credibility_signals"], ["recent growth"])

    def test_linkedin_lookup_prefers_person_profile(self):
        fake_tavily = types.ModuleType("tavily")
        fake_tavily.TavilyClient = FakeTavilyClient
        with patch.dict(sys.modules, {"tavily": fake_tavily}), patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}, clear=False):
            result = linkedin_lookup_node(
                founder_name="Shahad Bangla",
                company_name="Eallisto",
                domain="eallisto.com",
            )

        self.assertEqual(result["founder_linkedin"], "https://www.linkedin.com/in/shahad-bangla/")


if __name__ == "__main__":
    unittest.main()
