from flask import Blueprint, request, jsonify
from services.kmip_service import KMIPService
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


class KMIPRoutes:
    def __init__(self, kmip_service: KMIPService):
        self.kmip_service = kmip_service
        self.bp = Blueprint('kmip', __name__)
        self._register_routes()

    def _register_routes(self):
        self.bp.route('/get_barbican_id', methods=['GET'])(self.get_barbican_id)
        self.bp.route('/update_policy', methods=['POST'])(self.update_policy)
        self.bp.route('/kmip_register', methods=['POST'])(self.register_kmip)
        self.bp.route('/get_kmip_id_from_barbican', methods=['GET'])(self.get_kmip_id_from_barbican)
        self.bp.route('/update_owner', methods=['POST'])(self.update_owner)

    def get_barbican_id(self):
        if not is_authorized(request):
            return jsonify({"error": "Unauthorized"}), 401
        kmip_id = request.args.get('kmip_id')
        if not kmip_id:
            return jsonify({"error": "Missing kmip_id"}), 400
        logger.info("get_barbican_id called with kmip_id=%s", kmip_id)
        result = self.kmip_service.execute_mysql_queries(kmip_id)
        return jsonify(result)

    def update_policy(self):
        if not is_authorized(request):
            return jsonify({"error": "Unauthorized"}), 401
        data = request.get_json() or {}
        kmip_id = data.get('kmip_id')
        operation_policy_name = data.get('operation_policy_name')
        if not kmip_id or not operation_policy_name:
            return jsonify({"error": "Missing required parameters: 'kmip_id' and 'operation_policy_name'"}), 400
        logger.info("update_policy called with kmip_id=%s policy=%s", kmip_id, operation_policy_name)
        try:
            result = self.kmip_service.execute_mysql_queries(kmip_id, operation_policy_name=operation_policy_name)
            if "error" in result:
                return jsonify({"error": result["error"]}), 500
            return jsonify({
                "message": "Operation policy updated successfully",
                "kmip_id": kmip_id,
                "updated_policy": operation_policy_name,
                "details": result
            }), 200
        except Exception as e:
            logger.error("Unexpected error in update_policy: %s", e, exc_info=True)
            return jsonify({"error": "An internal error has occurred."}), 500

    def register_kmip(self):
        if not is_authorized(request):
            return jsonify({"error": "Unauthorized"}), 401
        data = request.get_json() or {}
        url = data.get('url')
        owner = data.get('owner')
        policy = data.get('policy')
        if not url or not owner or not policy:
            return jsonify({"error": "Missing parameters"}), 400
        logger.info("kmip_register called with owner=%s policy=%s", owner, policy)
        result = self.kmip_service.register_kmip_object(url, owner, policy)
        return jsonify(result)

    def get_kmip_id_from_barbican(self):
        if not is_authorized(request):
            return jsonify({"error": "Unauthorized"}), 401
        barbican_id = request.args.get('barbican_id')
        if not barbican_id:
            return jsonify({"error": "Missing barbican_id"}), 400
        logger.info("get_kmip_id_from_barbican called with barbican_id=%s", barbican_id)
        result = self.kmip_service.get_kmip_id_from_barbican(barbican_id)
        return jsonify(result)

    def update_owner(self):
        if not is_authorized(request):
            return jsonify({"error": "Unauthorized"}), 401
        data = request.get_json() or {}
        kmip_id = data.get('kmip_id')
        new_owner = data.get('new_owner')
        if not kmip_id or not new_owner:
            return jsonify({"error": "Missing required parameters: 'kmip_id' and 'new_owner'"}), 400
        logger.info("update_owner called with kmip_id=%s new_owner=%s", kmip_id, new_owner)
        try:
            result = self.kmip_service.execute_mysql_queries(kmip_id, owner=new_owner)
            if "error" in result:
                return jsonify({"error": result["error"]}), 500
            return jsonify({
                "message": "Owner updated successfully",
                "kmip_id": kmip_id,
                "new_owner": new_owner
            }), 200
        except Exception as e:
            logger.error("Unexpected error in update_owner: %s", e, exc_info=True)
            return jsonify({"error": "An internal error has occurred."}), 500
