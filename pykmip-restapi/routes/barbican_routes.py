from flask import Blueprint, request, jsonify
import requests
import os


def is_authorized(request):
    """
    Validates the token from the Authorization header against Keystone and
    ensures the user has the 'keymanager_admin' role.
    """
    keystone_url = os.environ.get("keystone_url")
    if not keystone_url:
        print("[Authorization Error] Keystone URL not set")
        return False

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        print("[Authorization Error] Missing or invalid Authorization header")
        return False

    token = auth_header.split("Bearer ")[1].strip()
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{keystone_url}/auth/tokens", headers=headers)
        response.raise_for_status()  # Raises for HTTP 4xx/5xx

        token_data = response.json().get("token", {})
        roles = token_data.get("roles", [])

        has_admin_role = any(role.get("name") == "keymanager_admin" for role in roles)
        if not has_admin_role:
            print("[Authorization Error] User lacks 'keymanager_admin' role")
        return has_admin_role

    except requests.exceptions.HTTPError as e:
        print(f"[Authorization Error] Keystone responded with HTTP error: {e.response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[Authorization Error] Network error while contacting Keystone: {e}")
    except ValueError as e:
        print(f"[Authorization Error] Failed to parse JSON: {e}")
    except KeyError as e:
        print(f"[Authorization Error] Expected key missing in token data: {e}")
    except Exception as e:
        print(f"[Authorization Error] Unexpected error: {e}")

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
        """
        Retrieves Barbican metadata for a given UUID.

        Returns:
            JSON response with metadata or error message.
        """
        if not is_authorized(request):
            return jsonify({"error": "Unauthorized"}), 401

        uuid = request.args.get('uuid')
        if not uuid:
            return jsonify({"error": "Missing uuid"}), 400

        result = self.barbican_service.get_metadata_from_uuid(uuid)
        return jsonify(result)

    def update_project_id(self):
        """
        Updates the project ID for a Barbican secret.

        Returns:
            JSON response indicating success or failure of the update.
        """
        if not is_authorized(request):
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json()
        secret_id = data.get('secret_id')
        project_id = data.get('project_id')

        if not secret_id or not project_id:
            return jsonify({"error": "Missing parameters"}), 400

        result = self.barbican_service.update_project_id(secret_id, project_id)
        return jsonify(result)