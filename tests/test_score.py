import unittest

from radar.score import score_opportunity


CONFIG = {
    "positive_signals": {
        "structured_source": 10,
        "legal": 15,
        "privacy": 16,
        "policy": 12,
        "research_writing": 12,
        "fellowship": 10,
        "remote": 10,
    },
    "negative_signals": {
        "advanced_role": -50,
        "qualified_professional_title": -35,
        "expired": -100,
    },
}


class ScoreOpportunityTests(unittest.TestCase):
    def test_search_query_does_not_leak_into_score(self):
        item = {
            "title": "Definition of policy",
            "description": "A general explanatory reference page.",
            "query": '"policy fellowship" Berlin',
            "url": "https://example.org/reference",
        }
        scored = score_opportunity(item, CONFIG)
        self.assertLess(scored["score"], 0)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertNotIn("fellowship", signals)

    def test_structured_privacy_role_can_pass_without_search_snippet_language(self):
        item = {
            "title": "Privacy Intern",
            "description": "Work on GDPR and data protection research.",
            "url": "https://example.org/jobs/1",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        self.assertGreaterEqual(scored["score"], 25)

    def test_senior_structured_role_is_penalised(self):
        item = {
            "title": "Senior Director, Privacy Policy",
            "description": "Lead privacy, legal and policy work.",
            "url": "https://example.org/jobs/2",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertIn("advanced_role", signals)

    def test_fellowship_receives_real_opportunity_signal(self):
        item = {
            "title": "Research Fellowship in AI Policy",
            "description": "Remote research and writing fellowship.",
            "url": "https://example.org/fellowship",
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertIn("opportunity_in_title", signals)
        self.assertIn("fellowship", signals)


if __name__ == "__main__":
    unittest.main()
