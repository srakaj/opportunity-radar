import unittest

from radar.score import score_opportunity


CONFIG = {
    "positive_signals": {
        "structured_source": 10,
        "legal": 15,
        "privacy": 16,
        "compliance": 14,
        "policy": 12,
        "governance": 12,
        "research_writing": 12,
        "international": 8,
        "berlin": 8,
        "leadership": 8,
    },
    "negative_signals": {
        "advanced_role": -50,
        "qualified_professional_title": -35,
        "outside_target_geography": -120,
    },
}


class SeniorityOverrideTests(unittest.TestCase):
    def test_associate_general_counsel_is_not_treated_as_entry_level(self):
        item = {
            "title": "Associate General Counsel, Product & IP",
            "description": (
                "Organisation: Example. Location: Berlin, Germany. Department: Legal. "
                "Lead product counseling, privacy, compliance, policy and governance work."
            ),
            "url": "https://example.org/jobs/agc",
            "source": "greenhouse:test",
            "location": "Berlin, Germany",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertIn("not_early_career", signals)
        self.assertIn("advanced_role", signals)
        self.assertLess(scored["score"], 25)

    def test_senior_legal_associate_cannot_use_associate_as_early_career_signal(self):
        item = {
            "title": "Senior Legal Associate",
            "description": "Organisation: Example. Location: Berlin. Department: Legal.",
            "url": "https://example.org/jobs/senior-associate",
            "source": "greenhouse:test",
            "location": "Berlin, Germany",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertIn("not_early_career", signals)
        self.assertIn("advanced_role", signals)
        self.assertLess(scored["score"], 25)


if __name__ == "__main__":
    unittest.main()
