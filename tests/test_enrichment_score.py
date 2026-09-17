import unittest

from radar.enrichment_score import reconcile_enrichment_score


CONFIG = {
    "positive_signals": {"paid": 8, "fellowship": 10, "traineeship": 10},
    "negative_signals": {"expired": -100},
}


class EnrichmentScoreTests(unittest.TestCase):
    def test_funding_possible_removes_false_paid_boost(self):
        item = {
            "score": 58,
            "compensation_status": "funding_possible",
            "deadline_status": "unknown",
            "reasons": [
                {"signal": "legal", "points": 15},
                {"signal": "paid", "points": 8},
            ],
        }
        result = reconcile_enrichment_score(item, CONFIG)
        self.assertEqual(result["score"], 50)
        self.assertNotIn("paid", {r["signal"] for r in result["reasons"]})

    def test_structured_paid_adds_paid_signal_when_missing(self):
        item = {
            "score": 50,
            "compensation_status": "paid",
            "deadline_status": "unknown",
            "reasons": [{"signal": "legal", "points": 15}],
        }
        result = reconcile_enrichment_score(item, CONFIG)
        self.assertEqual(result["score"], 58)
        self.assertIn("paid", {r["signal"] for r in result["reasons"]})

    def test_working_student_removes_incidental_traineeship_boost(self):
        item = {
            "score": 75,
            "opportunity_type": "Working student",
            "compensation_status": "unknown",
            "deadline_status": "unknown",
            "reasons": [
                {"signal": "legal", "points": 15},
                {"signal": "traineeship", "points": 10},
            ],
        }
        result = reconcile_enrichment_score(item, CONFIG)
        self.assertEqual(result["score"], 65)
        self.assertNotIn("traineeship", {r["signal"] for r in result["reasons"]})

    def test_structured_fellowship_restores_missing_fellowship_signal(self):
        item = {
            "score": 50,
            "opportunity_type": "Fellowship",
            "compensation_status": "unknown",
            "deadline_status": "unknown",
            "reasons": [{"signal": "legal", "points": 15}],
        }
        result = reconcile_enrichment_score(item, CONFIG)
        self.assertEqual(result["score"], 60)
        self.assertIn("fellowship", {r["signal"] for r in result["reasons"]})

    def test_expired_deadline_adds_penalty_once(self):
        item = {
            "score": 50,
            "compensation_status": "unknown",
            "deadline_status": "expired",
            "reasons": [{"signal": "legal", "points": 15}],
        }
        result = reconcile_enrichment_score(item, CONFIG)
        self.assertEqual(result["score"], -50)
        self.assertEqual(sum(1 for r in result["reasons"] if r["signal"] == "expired"), 1)


if __name__ == "__main__":
    unittest.main()
