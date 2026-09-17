import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DashboardWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        cls.app = (ROOT / "docs" / "app.js").read_text(encoding="utf-8")

    def test_workspace_controls_are_present(self):
        for marker in (
            'id="stageFilter"',
            'id="sortOrder"',
            'id="exportWorkspace"',
            'id="importWorkspace"',
            'class="workspace-panel"',
            'class="workspace-status"',
            'class="workspace-deadline"',
            'class="workspace-notes"',
        ):
            self.assertIn(marker, self.index)

    def test_workspace_is_private_browser_storage(self):
        self.assertIn("opportunity-radar-workspace-v1", self.app)
        self.assertIn("localStorage.getItem", self.app)
        self.assertIn("localStorage.setItem", self.app)
        self.assertIn("exportWorkspace", self.app)
        self.assertIn("importWorkspaceFile", self.app)

    def test_application_pipeline_stages_are_supported(self):
        for stage in (
            "Saved",
            "Interested",
            "Applying",
            "Applied",
            "Interview",
            "Offer",
            "Rejected",
            "Archived",
        ):
            self.assertIn(f"'{stage}'", self.app)

    def test_tracked_roles_survive_discovery_feed_removal(self):
        self.assertIn("trackedWorkspaceItems", self.app)
        self.assertIn("workspace_only", self.app)
        self.assertIn("no longer in the current discovery feed", self.app)


if __name__ == "__main__":
    unittest.main()
