from flask import Blueprint, request, jsonify
import requests
import os

def is_authorized(request):
    keystone_url = os.environ.get("keystone_url")
    if not keystone_url:
        return False

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return False

    token = auth_header.split("Bearer ")[1].strip()
    headers = {
        "X-Subject-Token": token,
        "Content-Type": "application/json"
    }

    try:
        resp = requests.get(f"{keystone_url}/auth/tokens", headers=headers)
        return resp.status_code == 200
    except requests.RequestException:
        return False


class BarbicanRoutes:
    def __init__(self, barbican_service):
        self.barbican_service = barbican_service
        self.bp = Blueprint('barbican', __name__)
        self._register_routes()

    def _register_routes(self):
        self.bp.route('/get_barbican_metadata', methods=['GET'])(self.get_metadata)
        self.bp.route('/update_project_id', methods=['POST'])(self.update_project_id)

    def get_metadata(self):
        if not is_authorized(request):
            return jsonify({"error": "Unauthorized"}), 401

        uuid = request.args.get('uuid')
        if not uuid:
            return jsonify({"error": "Missing uuid"}), 400

        result = self.barbican_service.get_metadata_from_uuid(uuid)
        return jsonify(result)

    def update_project_id(self):
        if not is_authorized(request):
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json()
        secret_id = data.get('secret_id')
        project_id = data.get('project_id')

        if not secret_id or not project_id:
            return jsonify({"error": "Missing parameters"}), 400

        result = self.barbican_service.update_project_id(secret_id, project_id)
        return jsonify(result)
