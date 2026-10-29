import unittest
from unittest.mock import MagicMock, patch
from mysql.connector import Error
from services.kmip_service import KMIPService


class TestKMIPServiceDecodeResult(unittest.TestCase):
    def setUp(self):
        self.service = KMIPService(db_config={})

    def test_decode_bytes_values(self):
        result = {"key": b"value", "other": 42}
        decoded = self.service.decode_result(result)
        self.assertEqual(decoded["key"], "value")
        self.assertEqual(decoded["other"], 42)

    def test_decode_bytearray_values(self):
        result = {"key": bytearray(b"hello")}
        decoded = self.service.decode_result(result)
        self.assertEqual(decoded["key"], "hello")

    def test_decode_non_bytes_unchanged(self):
        result = {"a": 1, "b": "str", "c": None}
        decoded = self.service.decode_result(result)
        self.assertEqual(decoded, result)

    def test_decode_none_input_returns_none(self):
        self.assertIsNone(self.service.decode_result(None))


class TestKMIPServiceConnect(unittest.TestCase):
    def setUp(self):
        self.service = KMIPService(db_config={"host": "localhost"})

    @patch('services.kmip_service.mysql.connector.connect')
    def test_connect_creates_new_connection(self, mock_connect):
        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_connect.return_value = mock_conn
        conn = self.service.connect()
        self.assertEqual(conn, mock_conn)
        mock_connect.assert_called_once()

    @patch('services.kmip_service.mysql.connector.connect')
    def test_connect_reuses_existing_live_connection(self, mock_connect):
        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        self.service.connection = mock_conn
        conn = self.service.connect()
        mock_connect.assert_not_called()
        self.assertEqual(conn, mock_conn)

    @patch('services.kmip_service.mysql.connector.connect')
    def test_connect_reconnects_when_disconnected(self, mock_connect):
        old_conn = MagicMock()
        old_conn.is_connected.return_value = False
        self.service.connection = old_conn
        new_conn = MagicMock()
        new_conn.is_connected.return_value = True
        mock_connect.return_value = new_conn
        conn = self.service.connect()
        mock_connect.assert_called_once()
        self.assertEqual(conn, new_conn)

    @patch('services.kmip_service.mysql.connector.connect')
    def test_connect_raises_on_db_error(self, mock_connect):
        mock_connect.side_effect = Error("connection refused")
        with self.assertRaises(Error):
            self.service.connect()


class TestKMIPServiceExecuteMysqlQueries(unittest.TestCase):
    def _make_service_with_mock_conn(self):
        service = KMIPService(db_config={})
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        service.connection = mock_conn
        service.connection.is_connected = MagicMock(return_value=True)
        return service, mock_conn, mock_cursor

    def test_select_success_extracts_barbican_id(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchone.return_value = {
            "uid": "42", "value": "https://barbican/secrets/abc-uuid"
        }
        mock_cursor.fetchall.return_value = []
        result = service.execute_mysql_queries("42")
        self.assertEqual(result["barbican_id"], "abc-uuid")
        self.assertIn("kmip_details", result)
        self.assertIsNone(result["query_executed"])

    def test_select_returns_error_when_not_found(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchone.return_value = None
        mock_cursor.fetchall.return_value = []
        result = service.execute_mysql_queries("nonexistent")
        self.assertIn("error", result)

    def test_select_with_policy_update_commits(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchone.return_value = {"uid": "42", "value": "https://x/abc"}
        mock_cursor.fetchall.return_value = []
        result = service.execute_mysql_queries("42", operation_policy_name="custom-policy")
        mock_conn.commit.assert_called()
        self.assertIsNotNone(result["query_executed"])
        self.assertIn("custom-policy", result["query_values"])

    def test_select_with_owner_update_commits(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchone.return_value = {"uid": "42", "value": "https://x/abc"}
        mock_cursor.fetchall.return_value = []
        result = service.execute_mysql_queries("42", owner="new-project")
        mock_conn.commit.assert_called()
        self.assertIsNotNone(result["query_executed"])
        self.assertIn("new-project", result["query_values"])

    def test_select_value_none_gives_none_barbican_id(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchone.return_value = {"uid": "42", "value": None}
        mock_cursor.fetchall.return_value = []
        result = service.execute_mysql_queries("42")
        self.assertIsNone(result["barbican_id"])

    def test_db_error_returns_error_dict(self):
        service = KMIPService(db_config={})
        with patch.object(service, 'connect', side_effect=Error("db error")):
            result = service.execute_mysql_queries("42")
        self.assertIn("error", result)
        self.assertIn("Database operation failed", result["error"])


class TestKMIPServiceRegisterKmipObject(unittest.TestCase):
    def _make_service_with_mock_conn(self):
        service = KMIPService(db_config={})
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        service.connection = mock_conn
        service.connection.is_connected = MagicMock(return_value=True)
        return service, mock_conn, mock_cursor

    def test_register_success_returns_uid(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchone.return_value = {"uid": 99}
        result = service.register_kmip_object(
            "https://barbican/secrets/abc", "project-x", "default"
        )
        self.assertIn("message", result)
        self.assertEqual(result["uid"], 99)
        self.assertEqual(mock_conn.commit.call_count, 2)

    def test_register_db_error_returns_error_dict(self):
        service = KMIPService(db_config={})
        with patch.object(service, 'connect', side_effect=Error("insert failed")):
            result = service.register_kmip_object("url", "owner", "policy")
        self.assertIn("error", result)
        self.assertIn("KMIP registration failed", result["error"])


class TestKMIPServiceGetKmipIdFromBarbican(unittest.TestCase):
    def _make_service_with_mock_conn(self):
        service = KMIPService(db_config={})
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        service.connection = mock_conn
        service.connection.is_connected = MagicMock(return_value=True)
        return service, mock_conn, mock_cursor

    def test_get_kmip_id_success(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchone.return_value = {"uid": 42}
        mock_cursor.fetchall.return_value = []
        result = service.get_kmip_id_from_barbican("barbican-abc")
        self.assertEqual(result["kmip_id"], 42)

    def test_get_kmip_id_not_found(self):
        service, mock_conn, mock_cursor = self._make_service_with_mock_conn()
        mock_cursor.fetchone.return_value = None
        mock_cursor.fetchall.return_value = []
        result = service.get_kmip_id_from_barbican("nonexistent")
        self.assertIn("error", result)
        self.assertIn("No KMIP ID found", result["error"])

    def test_get_kmip_id_db_error(self):
        service = KMIPService(db_config={})
        with patch.object(service, 'connect', side_effect=Error("query failed")):
            result = service.get_kmip_id_from_barbican("abc")
        self.assertIn("error", result)
        self.assertIn("Database operation failed", result["error"])


if __name__ == '__main__':
    unittest.main()
