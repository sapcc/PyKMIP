from flask import Blueprint, request, jsonify
import logging
import requests
import os

logger = logging.getLogger(__name__)


def is_authorized(request):
    keystone_url = os.environ.get("keystone_url")
    if not keystone_url:
        logger.error("Keystone URL not set")
        return False

    allowed_roles = {
        r.strip() for r in os.environ.get("ALLOWED_ADMIN_ROLES", "keymanager_admin").split(",") if r.strip()
    }

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        logger.warning("Missing or invalid Authorization header from %s", request.remote_addr)
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
        logger.debug("Validating token against Keystone: %s", keystone_url)
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning("Keystone returned %d for %s", resp.status_code, request.remote_addr)
            return False

        token = resp.json().get("token", {})
        role_names = {r.get("name") for r in token.get("roles", []) if isinstance(r, dict)}
        if not (allowed_roles & role_names):
            logger.warning("Token from %s lacks required role. Needed one of %s; got %s",
                           request.remote_addr, sorted(allowed_roles), sorted(role_names))
            return False
        return True

    except requests.exceptions.RequestException as e:
        logger.error("Keystone request error: %s", e)
    except ValueError:
        logger.error("Bad JSON from Keystone")
    except Exception as e:
        logger.error("Unexpected error during token validation: %s", e, exc_info=True)

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
        logger.info("get_barbican_metadata called with uuid=%s", uuid)
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
        logger.info("update_project_id called with secret_id=%s project_id=%s", secret_id, project_id)
        result = self.barbican_service.update_project_id(secret_id, project_id)
        return jsonify(result)
