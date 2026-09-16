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
        "fellowship": 10,
        "remote": 10,
    },
    "negative_signals": {
        "advanced_role": -50,
        "qualified_professional_title": -35,
        "open_source_discovery": -25,
        "non_mergeable_contribution": -60,
        "restricted_work_authorization": -120,
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

    def test_structured_privacy_intern_passes_job_board_gate(self):
        item = {
            "title": "Privacy Intern",
            "description": "Work on GDPR and data protection research.",
            "url": "https://example.org/jobs/1",
            "source": "greenhouse:test",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        self.assertGreaterEqual(scored["score"], 25)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertNotIn("not_early_career", signals)
        self.assertNotIn("outside_priority_domains", signals)

    def test_generic_software_intern_is_rejected_from_job_board(self):
        item = {
            "title": "Software Engineering Intern",
            "description": "Build distributed systems and backend infrastructure.",
            "url": "https://example.org/jobs/3",
            "source": "lever:test",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertIn("outside_priority_domains", signals)
        self.assertLess(scored["score"], 25)

    def test_finance_fellow_does_not_become_legal_from_late_description_words(self):
        item = {
            "title": "Finance Fellow",
            "description": (
                "Organisation: Example. Location: Remote. Department: Finance. "
                "Work on valuation and forecasting with financial models. "
                + "x" * 600
                + " Later sections mention compliance, legal policy and governance."
            ),
            "url": "https://example.org/jobs/finance",
            "source": "greenhouse:test",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertIn("outside_priority_domains", signals)
        self.assertLess(scored["score"], 25)

    def test_relevant_but_senior_job_is_rejected_from_job_board(self):
        item = {
            "title": "Senior Director, Privacy Policy",
            "description": "Lead privacy, legal and policy work globally.",
            "url": "https://example.org/jobs/2",
            "source": "greenhouse:test",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertIn("not_early_career", signals)
        self.assertIn("advanced_role", signals)
        self.assertLess(scored["score"], 25)

    def test_specialist_can_pass_with_explicit_entry_level_evidence(self):
        item = {
            "title": "Legal Operations Specialist",
            "description": "Entry-level role for a recent graduate. Support contract management and legal operations.",
            "url": "https://example.org/jobs/4",
            "source": "greenhouse:test",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertNotIn("not_early_career", signals)
        self.assertGreaterEqual(scored["score"], 25)

    def test_country_restricted_remote_role_is_penalised(self):
        item = {
            "title": "Legal Fellow",
            "description": "Fully remote. Candidates must be authorized to work in the United States.",
            "url": "https://example.org/jobs/us",
            "source": "greenhouse:test",
            "location": "United States",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertIn("restricted_work_authorization", signals)
        self.assertLess(scored["score"], 25)

    def test_open_source_issue_is_deprioritised_against_formal_roles(self):
        item = {
            "title": "Improve legal licensing documentation",
            "description": "Open-source contribution opportunity. Labels: help wanted, legal, licensing.",
            "url": "https://github.com/example/project/issues/1",
            "source": "github-issues-api",
            "structured_opportunity": True,
        }
        scored = score_opportunity(item, CONFIG)
        signals = {reason["signal"] for reason in scored["reasons"]}
        self.assertIn("open_source_discovery", signals)

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
