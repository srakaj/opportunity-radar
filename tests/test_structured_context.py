import unittest

from radar.score import score_opportunity


CONFIG = {
    "positive_signals": {
        "structured_source": 10,
        "legal": 15,
        "privacy": 16,
        "compliance": 14,
        "human_rights": 15,
        "international": 8,
        "remote": 10,
        "leadership": 8,
    },
    "negative_signals": {
        "advanced_role": -50,
        "outside_target_geography": -120,
    },
}


class StructuredRoleContextTests(unittest.TestCase):
    def test_tax_analyst_is_not_a_compliance_role_merely_from_body_text(self):
        item = {
            "title": "Tax Analyst",
            "description": (
                "Organisation: Spotify. Location: Stockholm. Commitment: Permanent. "
                "Team: Accounting. Department: Finance. "
                "This role focuses on global indirect tax compliance and reporting."
            ),
            "url": "https://example.org/jobs/tax",
            "source": "lever:test",
            "location": "Stockholm",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertIn("outside_priority_domains", signals)
        self.assertLess(scored["score"], 25)

    def test_revenue_protection_is_not_humanitarian_or_legal_protection(self):
        item = {
            "title": "Fraud Analyst (Revenue Protection)",
            "description": (
                "Organisation: Spotify. Location: London. Commitment: Full Time. "
                "Team: Operations and Strategy. Department: Markets and Subscriber Growth. "
                "Protect revenue and reduce payment fraud."
            ),
            "url": "https://example.org/jobs/fraud",
            "source": "lever:test",
            "location": "London",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertIn("outside_priority_domains", signals)
        self.assertLess(scored["score"], 25)

    def test_humanitarian_protection_category_remains_relevant(self):
        item = {
            "title": "Protection Assistant",
            "description": (
                "Organisation: NGO. Location: Germany. "
                "Career categories: Protection and Human Rights. Application deadline: 2026-10-01."
            ),
            "url": "https://example.org/jobs/protection",
            "source": "reliefweb-api-v2",
            "location": "Germany",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertNotIn("outside_priority_domains", signals)
        self.assertGreaterEqual(scored["score"], 25)

    def test_data_protection_title_remains_relevant_on_normal_job_board(self):
        item = {
            "title": "Data Protection Analyst",
            "description": "Organisation: Example. Location: Berlin. Department: Operations.",
            "url": "https://example.org/jobs/privacy",
            "source": "greenhouse:test",
            "location": "Berlin, Germany",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertNotIn("outside_priority_domains", signals)
        self.assertGreaterEqual(scored["score"], 25)


if __name__ == "__main__":
    unittest.main()
