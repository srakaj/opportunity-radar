import unittest

from radar.score import score_opportunity


CONFIG = {
    "positive_signals": {
        "structured_source": 10,
        "legal": 15,
        "privacy": 16,
        "compliance": 14,
        "policy": 12,
        "research_writing": 12,
        "international": 8,
    },
    "negative_signals": {
        "outside_target_geography": -120,
    },
}


class ExplicitRoleContextTests(unittest.TestCase):
    def test_software_intern_is_not_relabelled_by_deep_policy_prose(self):
        item = {
            "title": "Software Engineering Intern (Summer 2027)",
            "description": (
                "Organisation: Scale AI. Location: London, UK. Department: University. "
                "Build production software. Later sections discuss public policy, privacy, "
                "legal review and research collaborations across the company."
            ),
            "role_context": "Software Engineering Intern (Summer 2027) University",
            "url": "https://example.org/jobs/software-intern",
            "source": "greenhouse:test",
            "source_type": "job_board",
            "location": "London, UK",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertIn("outside_priority_domains", signals)
        self.assertLess(scored["score"], 25)

    def test_legal_intern_with_legal_department_still_passes(self):
        item = {
            "title": "Legal Intern",
            "description": "Organisation: Example. Location: Berlin. Department: Legal.",
            "role_context": "Legal Intern Legal",
            "url": "https://example.org/jobs/legal-intern",
            "source": "greenhouse:test",
            "source_type": "job_board",
            "location": "Berlin, Germany",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertNotIn("outside_priority_domains", signals)
        self.assertNotIn("outside_target_geography", signals)
        self.assertGreaterEqual(scored["score"], 25)

    def test_us_city_state_location_is_outside_target_geography(self):
        item = {
            "title": "Compliance Intern",
            "description": "Organisation: Example. Location: San Francisco, CA. Department: Legal.",
            "role_context": "Compliance Intern Legal",
            "url": "https://example.org/jobs/us-compliance",
            "source": "greenhouse:test",
            "source_type": "job_board",
            "location": "San Francisco, CA",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertIn("outside_target_geography", signals)
        self.assertLess(scored["score"], 25)


if __name__ == "__main__":
    unittest.main()
