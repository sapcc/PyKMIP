from flask import Blueprint, request, jsonify
import requests
import os

def is_authorized(request):
    """
    Validate Bearer token against Keystone v3 and ensure it has an allowed role.
    Minimal logging: only emit concise error reasons.
    """
    keystone_url = os.environ.get("keystone_url")  # e.g., https://keystone:5000/v3
    if not keystone_url:
        print("[Auth] Missing env keystone_url")
        return False

    allowed_roles = {
        r.strip() for r in os.environ.get("ALLOWED_ADMIN_ROLES", "keymanager_admin").split(",") if r.strip()
    }

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        print("[Auth] Missing/invalid Authorization header")
        return False

    subject_token = auth_header.split("Bearer ", 1)[1].strip()
    service_token = (os.environ.get("SERVICE_TOKEN") or subject_token).strip()

    headers = {
        "X-Auth-Token": service_token,
        "X-Subject-Token": subject_token,
        "Accept": "application/json",
    }
    url = keystone_url.rstrip("/") + "/auth/tokens"

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"[Auth] Keystone {resp.status_code}")
            return False

        token = resp.json().get("token", {})
        role_names = {r.get("name") for r in token.get("roles", []) if isinstance(r, dict)}
        if not (allowed_roles & role_names):
            print(f"[Auth] Missing required role. Needed one of {sorted(allowed_roles)}; got {sorted(role_names)}")
            return False
        return True

    except requests.exceptions.RequestException as e:
        print(f"[Auth] Keystone request error: {e}")
    except ValueError:
        print("[Auth] Bad JSON from Keystone")
    except Exception as e:
        print(f"[Auth] Unexpected: {e}")

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

        data = request.get_json() or {}
        secret_id = data.get('secret_id')
        project_id = data.get('project_id')

        if not secret_id or not project_id:
            return jsonify({"error": "Missing parameters"}), 400

        result = self.barbican_service.update_project_id(secret_id, project_id)
        return jsonify(result)
