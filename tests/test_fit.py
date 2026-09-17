import unittest

from radar.fit import assess_fit


PROFILE = {
    "education": {
        "law_student": True,
        "first_state_exam": False,
        "bar_admission": False,
    },
    "languages": ["German", "English"],
    "preferred_types": {
        "Working student": 14,
        "Fellowship": 12,
        "Internship": 11,
        "Traineeship": 8,
        "Early-career role": 7,
        "Open-source contribution": 5,
    },
    "target_domains": {
        "legal": 14,
        "privacy": 14,
        "legal_tech": 15,
        "legal_operations": 15,
        "compliance": 11,
        "ai_governance": 15,
        "policy": 9,
        "research_writing": 10,
    },
    "experience_signals": [
        "legal research",
        "privacy",
        "data protection",
        "compliance",
        "contract management",
        "legal operations",
        "legal tech",
    ],
    "fit_thresholds": {"strong_fit": 75, "stretch": 55},
}


def reason(signal, points=10):
    return {"signal": signal, "points": points}


class FitTests(unittest.TestCase):
    def test_remote_legal_fellowship_for_law_students_is_strong_fit(self):
        item = {
            "title": "Legal Fellow",
            "description": "Legal research, privacy and policy work.",
            "opportunity_type": "Fellowship",
            "work_model": "Remote",
            "location": "Remote",
            "languages": ["English"],
            "eligibility": ["Current law students"],
            "compensation_status": "unknown",
            "reasons": [reason("legal", 15), reason("privacy", 16), reason("policy", 12)],
        }
        result = assess_fit(item, PROFILE)
        self.assertEqual(result["fit_label"], "Strong fit")
        self.assertGreaterEqual(result["fit_score"], 75)
        self.assertIn("Explicitly open to current law students", result["fit_reasons"])

    def test_berlin_legal_working_student_is_strong_fit(self):
        item = {
            "title": "Working Student, Legal",
            "description": "Contract management, compliance and privacy support.",
            "opportunity_type": "Working student",
            "work_model": "Hybrid",
            "location": "Berlin, Germany",
            "languages": ["German", "English"],
            "eligibility": [],
            "compensation_status": "paid",
            "reasons": [reason("legal", 15), reason("privacy", 16), reason("compliance", 14)],
        }
        result = assess_fit(item, PROFILE)
        self.assertEqual(result["fit_label"], "Strong fit")
        self.assertIn("Berlin-based", result["fit_reasons"])
        self.assertIn("Explicit compensation signal", result["fit_reasons"])

    def test_rechtsreferendariat_mention_is_gap_not_hard_blocker(self):
        item = {
            "title": "Working Student, Legal",
            "description": "Legal and compliance support.",
            "opportunity_type": "Working student",
            "work_model": "Hybrid",
            "location": "Berlin, Germany",
            "languages": ["German"],
            "eligibility": ["Rechtsreferendar:innen"],
            "compensation_status": "paid",
            "reasons": [reason("legal", 15), reason("compliance", 14)],
        }
        result = assess_fit(item, PROFILE)
        self.assertFalse(result["fit_blockers"])
        self.assertTrue(any("Rechtsreferendariat" in gap for gap in result["fit_gaps"]))
        self.assertNotEqual(result["fit_label"], "Probably skip")

    def test_first_state_exam_requirement_becomes_probably_skip(self):
        item = {
            "title": "Legal Trainee",
            "description": "First State Exam required.",
            "opportunity_type": "Traineeship",
            "work_model": "Hybrid",
            "location": "Berlin, Germany",
            "languages": ["German"],
            "eligibility": ["First State Exam"],
            "compensation_status": "paid",
            "reasons": [reason("legal", 15)],
        }
        result = assess_fit(item, PROFILE)
        self.assertEqual(result["fit_label"], "Probably skip")
        self.assertIn("First State Exam appears required", result["fit_blockers"])

    def test_bar_admission_requirement_is_hard_blocker(self):
        item = {
            "title": "Privacy Counsel",
            "description": "Qualified lawyer required.",
            "opportunity_type": "Early-career role",
            "work_model": "Remote",
            "location": "Germany",
            "languages": ["English"],
            "eligibility": ["Bar admission required"],
            "compensation_status": "paid",
            "reasons": [reason("legal", 15), reason("privacy", 16)],
        }
        result = assess_fit(item, PROFILE)
        self.assertEqual(result["fit_label"], "Probably skip")
        self.assertIn("Bar admission appears required", result["fit_blockers"])

    def test_us_work_authorization_is_hard_blocker(self):
        item = {
            "title": "AI Policy Fellow",
            "description": "Policy and AI governance research.",
            "opportunity_type": "Fellowship",
            "work_model": "Remote",
            "location": "United States",
            "languages": ["English"],
            "eligibility": [],
            "work_authorization": "Candidates must be authorized to work in the United States without sponsorship",
            "compensation_status": "paid",
            "reasons": [reason("policy", 12), reason("ai_governance", 18)],
        }
        result = assess_fit(item, PROFILE)
        self.assertEqual(result["fit_label"], "Probably skip")
        self.assertTrue(any("Work-authorisation" in blocker for blocker in result["fit_blockers"]))

    def test_missing_language_creates_gap(self):
        item = {
            "title": "Legal Intern",
            "description": "Legal research role.",
            "opportunity_type": "Internship",
            "work_model": "Remote",
            "location": "Europe",
            "languages": ["French"],
            "eligibility": ["Current law students"],
            "compensation_status": "paid",
            "reasons": [reason("legal", 15), reason("research_writing", 12)],
        }
        result = assess_fit(item, PROFILE)
        self.assertTrue(any("French" in gap for gap in result["fit_gaps"]))


if __name__ == "__main__":
    unittest.main()
