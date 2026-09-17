import unittest
from datetime import datetime, timezone

from radar.deadline import enrich_deadline_timezone


class DeadlineTimezoneTests(unittest.TestCase):
    def test_explicit_eastern_time_is_converted_with_dst(self):
        item = {
            "title": "Legal Fellow",
            "location": "New York, NY",
            "description": "Application deadline: September 30, 2026 at 6:00 PM ET.",
            "deadline": "September 30, 2026",
        }
        result = enrich_deadline_timezone(item)
        self.assertEqual(result["deadline_time_confidence"], "explicit_timezone")
        self.assertEqual(result["deadline_source_timezone"], "ET")
        self.assertTrue(result["deadline_berlin_iso"].startswith("2026-10-01T00:00:00+02:00"))

    def test_explicit_pacific_time_is_converted_in_winter(self):
        item = {
            "title": "Policy Internship",
            "location": "San Francisco, CA",
            "description": "Applications close January 31, 2027 at 6:00 PM PT.",
            "deadline": "January 31, 2027",
        }
        result = enrich_deadline_timezone(item)
        self.assertEqual(result["deadline_time_confidence"], "explicit_timezone")
        self.assertTrue(result["deadline_berlin_iso"].startswith("2027-02-01T03:00:00+01:00"))

    def test_timezone_can_be_inferred_from_location(self):
        item = {
            "title": "Privacy Intern",
            "location": "San Francisco, CA",
            "description": "Application deadline: January 31, 2027 at 18:00.",
            "deadline": "January 31, 2027",
        }
        result = enrich_deadline_timezone(item)
        self.assertEqual(result["deadline_time_confidence"], "location_inferred")
        self.assertEqual(result["deadline_source_timezone"], "America/Los_Angeles")
        self.assertTrue(result["deadline_berlin_iso"].startswith("2027-02-01T03:00:00+01:00"))

    def test_date_only_defaults_to_2359_berlin_and_is_marked_assumed(self):
        item = {
            "title": "Research Fellowship",
            "location": "Remote",
            "description": "Application deadline: 29 January 2027.",
            "deadline": "29 January 2027",
        }
        result = enrich_deadline_timezone(item)
        self.assertEqual(result["deadline_time_confidence"], "date_only")
        self.assertFalse(result["deadline_time_explicit"])
        self.assertEqual(result["deadline_source_timezone"], "Europe/Berlin")
        self.assertTrue(result["deadline_berlin_iso"].startswith("2027-01-29T23:59:00+01:00"))

    def test_midnight_means_end_of_named_date(self):
        item = {
            "title": "US Fellowship",
            "location": "New York, NY",
            "description": "Applications are accepted until midnight ET on September 30, 2026.",
            "deadline": "September 30, 2026",
        }
        result = enrich_deadline_timezone(item)
        self.assertEqual(result["deadline_time_confidence"], "explicit_timezone")
        self.assertTrue(result["deadline_time_explicit"])
        self.assertTrue(result["deadline_berlin_iso"].startswith("2026-10-01T05:59:00+02:00"))

    def test_explicit_time_with_unknown_source_timezone_is_marked_uncertain(self):
        item = {
            "title": "Remote Legal Fellowship",
            "location": "Remote",
            "description": "Application deadline: 29 January 2027 at 18:00.",
            "deadline": "29 January 2027",
        }
        result = enrich_deadline_timezone(item)
        self.assertEqual(result["deadline_time_confidence"], "timezone_unknown")
        self.assertEqual(result["deadline_source_timezone"], "Europe/Berlin (fallback)")
        self.assertTrue(result["deadline_berlin_iso"].startswith("2027-01-29T18:00:00+01:00"))

    def test_precise_deadline_status_uses_time_not_just_date(self):
        item = {
            "title": "Legal Intern",
            "location": "Berlin, Germany",
            "description": "Application deadline: 17 September 2026 at 18:00 CET.",
            "deadline": "17 September 2026",
        }
        before = datetime(2026, 9, 17, 16, 30, tzinfo=timezone.utc)
        after = datetime(2026, 9, 17, 17, 30, tzinfo=timezone.utc)
        self.assertEqual(enrich_deadline_timezone(item, before)["deadline_status"], "closing_soon")
        self.assertEqual(enrich_deadline_timezone(item, after)["deadline_status"], "expired")


if __name__ == "__main__":
    unittest.main()
