import unittest
from unittest.mock import MagicMock, patch
from flask import Flask
from routes.barbican_routes import BarbicanRoutes
from services.barbican_service import BarbicanService


class TestBarbicanRoutes(unittest.TestCase):
    def setUp(self):
        self.barbican_service = MagicMock(spec=BarbicanService)
        self.barbican_routes = BarbicanRoutes(self.barbican_service)
        self.app = Flask(__name__)
        self.app.register_blueprint(self.barbican_routes.bp, url_prefix='/barbican')
        self.client = self.app.test_client()

    # --- get_barbican_metadata ---

    @patch('routes.barbican_routes.is_authorized', return_value=True)
    def test_get_metadata_success(self, mock_auth):
        self.barbican_service.get_metadata_from_uuid.return_value = {
            "data": [{"id": "uuid-1", "name": "test"}]
        }
        response = self.client.get('/barbican/get_barbican_metadata?uuid=test-uuid')
        self.assertEqual(response.status_code, 200)
        self.assertIn("data", response.json)

    @patch('routes.barbican_routes.is_authorized', return_value=True)
    def test_get_metadata_missing_uuid(self, mock_auth):
        response = self.client.get('/barbican/get_barbican_metadata')
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.barbican_routes.is_authorized', return_value=False)
    def test_get_metadata_unauthorized(self, mock_auth):
        response = self.client.get('/barbican/get_barbican_metadata?uuid=test-uuid')
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json)

    @patch('routes.barbican_routes.is_authorized', return_value=True)
    def test_get_metadata_not_found(self, mock_auth):
        self.barbican_service.get_metadata_from_uuid.return_value = {
            "error": "No metadata found for the given UUID"
        }
        response = self.client.get('/barbican/get_barbican_metadata?uuid=nonexistent')
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.json)

    @patch('routes.barbican_routes.is_authorized', return_value=True)
    def test_get_metadata_service_db_error(self, mock_auth):
        self.barbican_service.get_metadata_from_uuid.return_value = {
            "error": "Database error: Connection refused"
        }
        response = self.client.get('/barbican/get_barbican_metadata?uuid=test-uuid')
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.json)

    # --- update_project_id ---

    @patch('routes.barbican_routes.is_authorized', return_value=True)
    def test_update_project_id_success(self, mock_auth):
        self.barbican_service.update_project_id.return_value = {"message": "Project ID updated successfully"}
        response = self.client.post('/barbican/update_project_id', json={
            "secret_id": "test-secret-id",
            "project_id": "test-project-id"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json)

    @patch('routes.barbican_routes.is_authorized', return_value=True)
    def test_update_project_id_missing_secret_id(self, mock_auth):
        response = self.client.post('/barbican/update_project_id', json={"project_id": "p"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.barbican_routes.is_authorized', return_value=True)
    def test_update_project_id_missing_project_id(self, mock_auth):
        response = self.client.post('/barbican/update_project_id', json={"secret_id": "s"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.barbican_routes.is_authorized', return_value=True)
    def test_update_project_id_missing_parameters(self, mock_auth):
        response = self.client.post('/barbican/update_project_id', json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    @patch('routes.barbican_routes.is_authorized', return_value=False)
    def test_update_project_id_unauthorized(self, mock_auth):
        response = self.client.post('/barbican/update_project_id', json={
            "secret_id": "s", "project_id": "p"
        })
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json)

    @patch('routes.barbican_routes.is_authorized', return_value=True)
    def test_update_project_id_project_not_found(self, mock_auth):
        self.barbican_service.update_project_id.return_value = {
            "error": "No project found with the given external_id: p"
        }
        response = self.client.post('/barbican/update_project_id', json={
            "secret_id": "s", "project_id": "p"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.json)

    @patch('routes.barbican_routes.is_authorized', return_value=True)
    def test_update_project_id_secret_not_found(self, mock_auth):
        self.barbican_service.update_project_id.return_value = {
            "error": "No secret found with the given secret_id: s"
        }
        response = self.client.post('/barbican/update_project_id', json={
            "secret_id": "s", "project_id": "p"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.json)

    @patch('routes.barbican_routes.is_authorized', return_value=True)
    def test_update_project_id_service_db_error(self, mock_auth):
        self.barbican_service.update_project_id.return_value = {"error": "Database error: timeout"}
        response = self.client.post('/barbican/update_project_id', json={
            "secret_id": "s", "project_id": "p"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.json)


if __name__ == '__main__':
    unittest.main()
