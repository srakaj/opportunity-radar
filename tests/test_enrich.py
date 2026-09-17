import unittest
from datetime import datetime, timezone

from radar.enrich import deadline_status, enrich_opportunity


class EnrichmentTests(unittest.TestCase):
    def test_wikimedia_funding_is_not_marked_paid(self):
        item = {
            "title": "Legal Fellow (Spring 2027)",
            "description": (
                "Organisation: Wikimedia Foundation. Location: Remote. Department: Legal. "
                "Summary Current law students and recent law school graduates may apply. "
                "Fall and Spring fellowships have a duration of 18 weeks. "
                "The Legal Department will work with a fellow's university to facilitate "
                "earning academic credits and/or receiving funding for the fellow's time. "
                "Requirements High energy and commitment."
            ),
            "location": "Remote",
            "source_type": "job_board",
        }
        enriched = enrich_opportunity(item)
        self.assertEqual(enriched["opportunity_type"], "Fellowship")
        self.assertEqual(enriched["work_model"], "Remote")
        self.assertEqual(enriched["duration"], "18 weeks")
        self.assertEqual(enriched["compensation_status"], "funding_possible")
        self.assertNotEqual(enriched["compensation_status"], "paid")
        self.assertIn("Current law students", enriched["eligibility"])
        self.assertIn("Recent graduates", enriched["eligibility"])

    def test_explicit_salary_and_hybrid_commitment_are_extracted(self):
        item = {
            "title": "Privacy Intern",
            "description": (
                "This is a paid internship in a hybrid setup. Compensation is €18 per hour. "
                "Part-time, 20 hours per week. Fluent German and English required. "
                "Application deadline: 29 January 2027."
            ),
            "location": "Berlin, Germany",
            "source_type": "job_board",
        }
        enriched = enrich_opportunity(item)
        self.assertEqual(enriched["opportunity_type"], "Internship")
        self.assertEqual(enriched["work_model"], "Hybrid")
        self.assertEqual(enriched["compensation_status"], "paid")
        self.assertIn("€18", enriched["compensation"])
        self.assertIn("Part-time", enriched["commitment"])
        self.assertIn("20 hours per week", enriched["commitment"])
        self.assertEqual(enriched["deadline"], "29 January 2027")
        self.assertIn("German", enriched["languages"])
        self.assertIn("English", enriched["languages"])

    def test_working_student_title_wins_over_trainee_mention_in_body(self):
        item = {
            "title": "Working Student, Legal (German-speaking)",
            "description": (
                "As a Working Student you will join the legal team. "
                "For the Legal Trainee track this is a minimum 6-month placement, "
                "ideally starting in September 2026. The role is based in Berlin in a hybrid setup."
            ),
            "location": "Berlin, Germany",
            "source_type": "job_board",
        }
        enriched = enrich_opportunity(item)
        self.assertEqual(enriched["opportunity_type"], "Working student")
        self.assertEqual(enriched["duration"], "6 months")
        self.assertEqual(enriched["work_model"], "Hybrid")
        self.assertEqual(enriched["start_date"], "September 2026")

    def test_german_hybrid_and_minimum_duration_are_extracted(self):
        item = {
            "title": "Werkstudent:in, Recht",
            "description": (
                "Dies ist eine Station mit einer Mindestdauer von 6 Monaten. "
                "Die Stelle ist in Berlin angesiedelt, im hybriden Arbeitsmodell."
            ),
            "location": "Berlin, Germany",
            "source_type": "job_board",
        }
        enriched = enrich_opportunity(item)
        self.assertEqual(enriched["opportunity_type"], "Working student")
        self.assertEqual(enriched["duration"], "6 Monaten")
        self.assertEqual(enriched["work_model"], "Hybrid")

    def test_unpaid_overrides_generic_compensation_language(self):
        item = {
            "title": "Legal Internship",
            "description": "This is an unpaid internship. No compensation is provided.",
            "source_type": "job_board",
        }
        enriched = enrich_opportunity(item)
        self.assertEqual(enriched["compensation_status"], "unpaid")

    def test_work_authorization_sentence_is_preserved(self):
        item = {
            "title": "Policy Fellow",
            "description": (
                "Remote fellowship. Candidates must be authorized to work in the United States. "
                "No visa sponsorship is available."
            ),
            "location": "United States",
            "source_type": "job_board",
        }
        enriched = enrich_opportunity(item)
        self.assertIn("authorized to work", enriched["work_authorization"].lower())

    def test_deadline_status(self):
        now = datetime(2026, 9, 17, tzinfo=timezone.utc)
        self.assertEqual(deadline_status("2026-09-16", now), "expired")
        self.assertEqual(deadline_status("22 September 2026", now), "closing_soon")
        self.assertEqual(deadline_status("29 January 2027", now), "open")
        self.assertEqual(deadline_status("rolling", now), "unknown")

    def test_rechtsreferendar_and_first_exam_eligibility(self):
        item = {
            "title": "Legal Trainee",
            "description": (
                "Geeignet für Rechtsreferendar:innen. Voraussetzung ist das Erste Staatsexamen. "
                "Dauer: 6 Monate."
            ),
            "location": "Berlin, Germany",
            "source_type": "job_board",
        }
        enriched = enrich_opportunity(item)
        self.assertEqual(enriched["opportunity_type"], "Traineeship")
        self.assertIn("Rechtsreferendar:innen", enriched["eligibility"])
        self.assertIn("First State Exam", enriched["eligibility"])
        self.assertEqual(enriched["duration"], "6 Monate")


if __name__ == "__main__":
    unittest.main()
