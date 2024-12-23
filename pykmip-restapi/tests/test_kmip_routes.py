
import unittest
from unittest.mock import MagicMock
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

    def test_get_barbican_id_success(self):
        self.kmip_service.execute_mysql_queries.return_value = {"barbican_id": "test-barbican-id"}
        response = self.client.get('/kmip/get_barbican_id?kmip_id=12345')
        self.assertEqual(response.status_code, 200)
        self.assertIn("barbican_id", response.json)

    def test_get_barbican_id_missing_kmip_id(self):
        response = self.client.get('/kmip/get_barbican_id')
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    def test_register_kmip_missing_parameters(self):
        response = self.client.post('/kmip/kmip_register', json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)
