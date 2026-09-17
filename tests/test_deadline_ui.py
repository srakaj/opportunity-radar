import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class DeadlineUiTests(unittest.TestCase):
    def test_dashboard_loads_deadline_assets(self):
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn("deadline-ui.css", html)
        self.assertIn("deadline-ui.js", html)
        self.assertIn("UI 0.5.1", html)

    def test_deadline_renderer_uses_berlin_and_german_format(self):
        js = (ROOT / "docs" / "deadline-ui.js").read_text(encoding="utf-8")
        self.assertIn("Europe/Berlin", js)
        self.assertIn("de-DE", js)
        self.assertIn("Deadline (Berlin)", js)
        self.assertIn("TZ inferred", js)
        self.assertIn("time assumed", js)
        self.assertIn("TZ unknown", js)

    def test_assumed_deadline_is_visually_distinct(self):
        css = (ROOT / "docs" / "deadline-ui.css").read_text(encoding="utf-8")
        self.assertIn(".deadline-assumed .deadline-value", css)
        self.assertIn("font-style: italic", css)


if __name__ == "__main__":
    unittest.main()
