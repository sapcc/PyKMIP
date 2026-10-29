import unittest
from unittest.mock import MagicMock, patch
from flask import Flask
from routes.kmip_routes import KMIPRoutes
from services.kmip_service import KMIPService


class TestKMIPRoutes(unittest.TestCase):
    def setUp(self):
        self.kmip_service = MagicMock(spec=KMIPService)
        self.kmip_routes = KMIPRoutes(self.kmip_service)
        self.app = Flask(__name__)
        self.app.register_blueprint(self.kmip_routes.bp, url_prefix='/kmip')
        self.client = self.app.test_client()

    # --- get_barbican_id ---

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_get_barbican_id_success(self, mock_auth):
        self.kmip_service.execute_mysql_queries.return_value = {"barbican_id": "test-barbican-id"}
        response = self.client.get('/kmip/get_barbican_id?kmip_id=12345')
        self.assertEqual(response.status_code, 200)
        self.assertIn("barbican_id", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_get_barbican_id_missing_kmip_id(self, mock_auth):
        response = self.client.get('/kmip/get_barbican_id')
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=False)
    def test_get_barbican_id_unauthorized(self, mock_auth):
        response = self.client.get('/kmip/get_barbican_id?kmip_id=12345')
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json)

    # --- update_policy ---

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_update_policy_success(self, mock_auth):
        self.kmip_service.execute_mysql_queries.return_value = {
            "barbican_id": "bid", "kmip_details": {}
        }
        response = self.client.post('/kmip/update_policy', json={
            "kmip_id": "12345",
            "operation_policy_name": "default"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json)
        self.assertEqual(response.json["kmip_id"], "12345")
        self.assertEqual(response.json["updated_policy"], "default")

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_update_policy_missing_kmip_id(self, mock_auth):
        response = self.client.post('/kmip/update_policy', json={"operation_policy_name": "default"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_update_policy_missing_policy_name(self, mock_auth):
        response = self.client.post('/kmip/update_policy', json={"kmip_id": "12345"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_update_policy_missing_both(self, mock_auth):
        response = self.client.post('/kmip/update_policy', json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=False)
    def test_update_policy_unauthorized(self, mock_auth):
        response = self.client.post('/kmip/update_policy', json={
            "kmip_id": "12345", "operation_policy_name": "default"
        })
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_update_policy_service_returns_error(self, mock_auth):
        self.kmip_service.execute_mysql_queries.return_value = {"error": "DB failure"}
        response = self.client.post('/kmip/update_policy', json={
            "kmip_id": "12345", "operation_policy_name": "default"
        })
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_update_policy_service_raises_exception(self, mock_auth):
        self.kmip_service.execute_mysql_queries.side_effect = Exception("Unexpected")
        response = self.client.post('/kmip/update_policy', json={
            "kmip_id": "12345", "operation_policy_name": "default"
        })
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.json)

    # --- register_kmip ---

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_register_kmip_success(self, mock_auth):
        self.kmip_service.register_kmip_object.return_value = {
            "message": "KMIP object registered successfully", "uid": 42
        }
        response = self.client.post('/kmip/kmip_register', json={
            "url": "https://barbican/secrets/abc",
            "owner": "project-xyz",
            "policy": "default"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("uid", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_register_kmip_missing_all_parameters(self, mock_auth):
        response = self.client.post('/kmip/kmip_register', json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_register_kmip_missing_url(self, mock_auth):
        response = self.client.post('/kmip/kmip_register', json={"owner": "p", "policy": "default"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_register_kmip_missing_owner(self, mock_auth):
        response = self.client.post('/kmip/kmip_register', json={"url": "https://x", "policy": "default"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_register_kmip_missing_policy(self, mock_auth):
        response = self.client.post('/kmip/kmip_register', json={"url": "https://x", "owner": "p"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=False)
    def test_register_kmip_unauthorized(self, mock_auth):
        response = self.client.post('/kmip/kmip_register', json={
            "url": "https://x", "owner": "p", "policy": "default"
        })
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json)

    # --- get_kmip_id_from_barbican ---

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_get_kmip_id_from_barbican_success(self, mock_auth):
        self.kmip_service.get_kmip_id_from_barbican.return_value = {"kmip_id": 99}
        response = self.client.get('/kmip/get_kmip_id_from_barbican?barbican_id=abc-uuid')
        self.assertEqual(response.status_code, 200)
        self.assertIn("kmip_id", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_get_kmip_id_from_barbican_missing_id(self, mock_auth):
        response = self.client.get('/kmip/get_kmip_id_from_barbican')
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=False)
    def test_get_kmip_id_from_barbican_unauthorized(self, mock_auth):
        response = self.client.get('/kmip/get_kmip_id_from_barbican?barbican_id=abc')
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_get_kmip_id_from_barbican_not_found(self, mock_auth):
        self.kmip_service.get_kmip_id_from_barbican.return_value = {
            "error": "No KMIP ID found for Barbican ID: abc"
        }
        response = self.client.get('/kmip/get_kmip_id_from_barbican?barbican_id=abc')
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.json)

    # --- update_owner ---

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_update_owner_success(self, mock_auth):
        self.kmip_service.execute_mysql_queries.return_value = {"barbican_id": "bid"}
        response = self.client.post('/kmip/update_owner', json={
            "kmip_id": "12345", "new_owner": "new-project"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json)
        self.assertEqual(response.json["new_owner"], "new-project")

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_update_owner_missing_kmip_id(self, mock_auth):
        response = self.client.post('/kmip/update_owner', json={"new_owner": "x"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_update_owner_missing_new_owner(self, mock_auth):
        response = self.client.post('/kmip/update_owner', json={"kmip_id": "12345"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_update_owner_missing_both(self, mock_auth):
        response = self.client.post('/kmip/update_owner', json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=False)
    def test_update_owner_unauthorized(self, mock_auth):
        response = self.client.post('/kmip/update_owner', json={
            "kmip_id": "12345", "new_owner": "x"
        })
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_update_owner_service_returns_error(self, mock_auth):
        self.kmip_service.execute_mysql_queries.return_value = {"error": "not found"}
        response = self.client.post('/kmip/update_owner', json={
            "kmip_id": "12345", "new_owner": "x"
        })
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.json)

    @patch('routes.kmip_routes.is_authorized', return_value=True)
    def test_update_owner_service_raises_exception(self, mock_auth):
        self.kmip_service.execute_mysql_queries.side_effect = Exception("Unexpected")
        response = self.client.post('/kmip/update_owner', json={
            "kmip_id": "12345", "new_owner": "x"
        })
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.json)


if __name__ == '__main__':
    unittest.main()
