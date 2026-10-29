import unittest
from unittest.mock import MagicMock, patch
from mysql.connector import Error
from services.barbican_service import BarbicanService


class TestBarbicanServiceGetMetadata(unittest.TestCase):
    def _make_service_with_mock_conn(self):
        service = BarbicanService(db_config={})
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        service.connection = mock_conn
        service.cursor = mock_cursor
        service.connection.is_connected = MagicMock(return_value=True)
        return service, mock_conn, mock_cursor

    def test_get_metadata_success_returns_data(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchall.return_value = [{
            "id": "uuid-1", "name": "secret", "algorithm": "aes",
            "bit_length": 256, "mode": None, "secret_type": "symmetric",
            "status": "ACTIVE", "created_at": "2024-01-01", "updated_at": "2024-01-02",
            "deleted": 0, "deleted_at": None, "expiration": None,
            "creator_id": "user1", "project_id": "proj-ext-id"
        }]
        result = service.get_metadata_from_uuid("uuid-1")
        self.assertIn("data", result)
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["id"], "uuid-1")

    def test_get_metadata_not_found_returns_error(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchall.return_value = []
        result = service.get_metadata_from_uuid("nonexistent")
        self.assertIn("error", result)
        self.assertEqual(result["error"], "No metadata found for the given UUID")

    def test_get_metadata_bytearray_fields_decoded(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchall.return_value = [{
            "id": bytearray(b"uuid-bytes"), "name": "test", "algorithm": None,
            "bit_length": 256, "mode": None, "secret_type": "symmetric",
            "status": "ACTIVE", "created_at": "2024-01-01", "updated_at": "2024-01-02",
            "deleted": 0, "deleted_at": None, "expiration": None,
            "creator_id": None, "project_id": "proj"
        }]
        result = service.get_metadata_from_uuid("uuid-1")
        self.assertIn("data", result)
        self.assertEqual(result["data"][0]["id"], "uuid-bytes")

    def test_get_metadata_db_error_returns_error(self):
        service = BarbicanService(db_config={})
        with patch.object(service, 'connect', side_effect=Error("connection failed")):
            result = service.get_metadata_from_uuid("uuid-1")
        self.assertIn("error", result)
        self.assertIn("Database error", result["error"])


class TestBarbicanServiceUpdateProjectId(unittest.TestCase):
    def _make_service_with_mock_conn(self):
        service = BarbicanService(db_config={})
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        service.connection = mock_conn
        service.cursor = mock_cursor
        service.connection.is_connected = MagicMock(return_value=True)
        return service, mock_conn, mock_cursor

    def test_update_project_id_success(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchone.return_value = {"id": "internal-proj-id"}
        mock_cursor.rowcount = 1
        result = service.update_project_id("secret-id", "external-proj-id")
        self.assertEqual(result["message"], "Project ID updated successfully")
        mock_conn.commit.assert_called_once()

    def test_update_project_id_project_not_found(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchone.return_value = None
        result = service.update_project_id("secret-id", "nonexistent-external-id")
        self.assertIn("error", result)
        self.assertIn("No project found", result["error"])

    def test_update_project_id_secret_not_found(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchone.return_value = {"id": "internal-proj-id"}
        mock_cursor.rowcount = 0
        result = service.update_project_id("nonexistent-secret", "external-proj-id")
        self.assertIn("error", result)
        self.assertIn("No secret found", result["error"])

    def test_update_project_id_bytearray_project_id_decoded(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchone.return_value = {"id": bytearray(b"internal-id")}
        mock_cursor.rowcount = 1
        result = service.update_project_id("secret-id", "external-proj-id")
        self.assertEqual(result["message"], "Project ID updated successfully")

    def test_update_project_id_db_error_returns_error(self):
        service = BarbicanService(db_config={})
        with patch.object(service, 'connect', side_effect=Error("db error")):
            result = service.update_project_id("s", "p")
        self.assertIn("error", result)
        self.assertIn("Database error", result["error"])


if __name__ == '__main__':
    unittest.main()
