import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class SourceUiTests(unittest.TestCase):
    def test_dashboard_loads_v06_source_assets(self):
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn("UI 0.6.0", html)
        self.assertIn("source-ui.css", html)
        self.assertIn("source-ui.js", html)

    def test_source_ui_exposes_health_and_provenance(self):
        js = (ROOT / "docs" / "source-ui.js").read_text(encoding="utf-8")
        self.assertIn("Sources ${totals.healthy", js)
        self.assertIn("Source quality", js)
        self.assertIn("Last checked", js)
        self.assertIn("source-health.json", js)
        self.assertIn("duplicate", js)

    def test_source_health_file_has_expected_shape(self):
        health = (ROOT / "docs" / "source-health.json").read_text(encoding="utf-8")
        self.assertIn('"summary"', health)
        self.assertIn('"sources"', health)


if __name__ == "__main__":
    unittest.main()
