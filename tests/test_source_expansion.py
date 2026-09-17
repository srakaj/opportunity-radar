import unittest
from unittest.mock import Mock, patch

from radar.source_expansion import (
    annotate_source,
    build_watchlist_queries,
    canonical_url,
    fetch_ashby_board,
    merge_opportunities,
    opportunity_identity,
)


SOURCE_CFG = {
    "watchlist": {
        "enabled": True,
        "max_queries_per_run": 2,
        "organizations": [
            {"name": "BRYTER", "domain": "bryter.com"},
            {"name": "noyb", "domain": "noyb.eu"},
        ],
    }
}


class SourceExpansionTests(unittest.TestCase):
    def test_tracking_params_do_not_create_new_url_identity(self):
        left = canonical_url("https://example.com/jobs/123?utm_source=test&ref=abc")
        right = canonical_url("https://example.com/jobs/123")
        self.assertEqual(left, right)

    def test_role_identity_uses_org_title_and_location(self):
        first = {
            "title": "Working Student, Legal",
            "organization": "Example GmbH",
            "location": "Berlin, Germany",
            "url": "https://jobs.example/a",
        }
        second = {
            "title": "Working Student Legal",
            "organization": "Example GmbH",
            "location": "Berlin Germany",
            "url": "https://other.example/b",
        }
        self.assertEqual(opportunity_identity(first), opportunity_identity(second))

    def test_official_ats_beats_web_duplicate(self):
        web = {
            "title": "Legal Intern",
            "url": "https://search.example/job",
            "description": "short snippet",
            "source": "duckduckgo-html",
            "source_quality": "Web discovery",
            "source_priority": 40,
            "organization": "Example",
            "location": "Berlin",
        }
        ats = {
            "title": "Legal Intern",
            "url": "https://jobs.example/job/123",
            "description": "full official description",
            "source": "ashby:example",
            "source_quality": "Official ATS",
            "source_priority": 100,
            "organization": "Example",
            "location": "Berlin",
            "structured_opportunity": True,
        }
        merged = merge_opportunities(web, ats)
        self.assertEqual(merged["source"], "ashby:example")
        self.assertEqual(merged["source_quality"], "Official ATS")
        self.assertEqual(merged["duplicate_count"], 1)
        self.assertEqual(len(merged["alternate_sources"]), 2)

    def test_watchlist_domain_is_treated_as_official_site(self):
        item = {
            "title": "Legal Operations Intern",
            "url": "https://www.bryter.com/careers/legal-ops",
            "source": "duckduckgo-html",
        }
        annotated = annotate_source(item, SOURCE_CFG)
        self.assertEqual(annotated["source_quality"], "Official site")
        self.assertEqual(annotated["source_priority"], 90)
        self.assertEqual(annotated["organization"], "BRYTER")
        self.assertTrue(annotated["watchlist_match"])

    def test_watchlist_query_limit_is_respected(self):
        queries = build_watchlist_queries(SOURCE_CFG)
        self.assertEqual(len(queries), 2)
        self.assertIn("site:bryter.com", queries[0]["query"])

    @patch("radar.source_expansion.requests.get")
    def test_ashby_board_is_normalised(self, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "jobs": [
                {
                    "title": "Legal AI Student Analyst",
                    "location": "Remote",
                    "department": "Product",
                    "team": "Legal Engineering",
                    "employmentType": "Contract",
                    "workplaceType": "Remote",
                    "descriptionHtml": "<p>Work on legal AI evaluation.</p>",
                    "jobUrl": "https://jobs.ashbyhq.com/example/abc",
                    "publishedAt": "2026-09-17T10:00:00Z",
                }
            ]
        }
        mock_get.return_value = response

        rows = fetch_ashby_board({"board": "example", "name": "Example AI"})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "ashby:example")
        self.assertEqual(rows[0]["organization"], "Example AI")
        self.assertIn("Work on legal AI evaluation.", rows[0]["description"])
        self.assertTrue(rows[0]["structured_opportunity"])


if __name__ == "__main__":
    unittest.main()
