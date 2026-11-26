import unittest
from unittest.mock import MagicMock, patch

from services.barbican_service import BarbicanService


class TestBarbicanServiceUpdateProjectId(unittest.TestCase):
    def setUp(self):
        self.service = BarbicanService({})
        self.cursor = MagicMock()
        self.connection = MagicMock()
        # BarbicanService.connect() returns the cursor and sets self.connection
        self.service.connection = self.connection
        self.service.cursor = self.cursor
        patcher = patch.object(BarbicanService, "connect", return_value=self.cursor)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_update_project_id_noop_succeeds(self):
        """A no-op update (secret already has this project_id) must succeed.

        Regression: previously the code read cursor.rowcount after the UPDATE,
        which MySQL reports as rows *changed* (0 for a no-op), causing a false
        'No secret found' error for secrets that genuinely exist.
        """
        # 1) find project by external_id -> internal id
        # 2) existence SELECT -> secret exists
        self.cursor.fetchone.side_effect = [{"id": "internal-project-id"}, (1,)]
        # Simulate MySQL no-op: row matched but unchanged.
        self.cursor.rowcount = 0

        result = self.service.update_project_id("existing-secret", "external-proj-uuid")

        self.assertEqual(result, {"message": "Project ID updated successfully"})
        self.connection.commit.assert_called_once()

    def test_update_project_id_missing_project(self):
        self.cursor.fetchone.side_effect = [None]
        result = self.service.update_project_id("any-secret", "unknown-external")
        self.assertIn("No project found", result["error"])
        self.connection.commit.assert_not_called()

    def test_update_project_id_missing_secret(self):
        # project found, but secret existence SELECT returns nothing
        self.cursor.fetchone.side_effect = [{"id": "internal-project-id"}, None]
        result = self.service.update_project_id("ghost-secret", "external-proj-uuid")
        self.assertIn("No secret found", result["error"])
        self.connection.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
