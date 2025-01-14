from flask import Blueprint, request, jsonify
from services.kmip_service import KMIPService

class KMIPRoutes:
    def __init__(self, kmip_service):
        self.kmip_service = kmip_service
        self.bp = Blueprint('kmip', __name__)
        self._register_routes()

    def _register_routes(self):
        self.bp.route('/get_barbican_id', methods=['GET'])(self.get_barbican_id)
        self.bp.route('/update_policy', methods=['POST'])(self.update_policy)
        self.bp.route('/kmip_register', methods=['POST'])(self.register_kmip)
        self.bp.route('/get_kmip_id_from_barbican', methods=['GET'])(self.get_kmip_id_from_barbican)

    def get_barbican_id(self):
        kmip_id = request.args.get('kmip_id')
        if not kmip_id:
            return jsonify({"error": "Missing kmip_id"}), 400
        result = self.kmip_service.execute_mysql_queries(kmip_id)
        return jsonify(result)

    def update_policy(self):
        data = request.get_json()
        return jsonify({"message": "Update policy logic goes here"})

    def register_kmip(self):
        data = request.get_json()
        url = data.get('url')
        owner = data.get('owner')
        policy = data.get('policy')
        if not url or not owner or not policy:
            return jsonify({"error": "Missing parameters"}), 400
        result = self.kmip_service.register_kmip_object(url, owner, policy)
        return jsonify(result)

    def get_kmip_id_from_barbican(self):
        barbican_id = request.args.get('barbican_id')
        if not barbican_id:
            return jsonify({"error": "Missing barbican_id"}), 400
        result = self.kmip_service.get_kmip_id_from_barbican(barbican_id)
        return jsonify(result)
