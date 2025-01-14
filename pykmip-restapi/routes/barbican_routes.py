from flask import Blueprint, request, jsonify

class BarbicanRoutes:
    def __init__(self, barbican_service):
        self.barbican_service = barbican_service
        self.bp = Blueprint('barbican', __name__)
        self._register_routes()

    def _register_routes(self):
        self.bp.route('/get_barbican_metadata', methods=['GET'])(self.get_metadata)
        self.bp.route('/update_project_id', methods=['POST'])(self.update_project_id)

    def get_metadata(self):
        uuid = request.args.get('uuid')
        if not uuid:
            return jsonify({"error": "Missing uuid"}), 400

        result = self.barbican_service.get_metadata_from_uuid(uuid)
        return jsonify(result)

    def update_project_id(self):
        data = request.get_json()
        secret_id = data.get('secret_id')
        project_id = data.get('project_id')

        if not secret_id or not project_id:
            return jsonify({"error": "Missing parameters"}), 400

        result = self.barbican_service.update_project_id(secret_id, project_id)
        return jsonify(result)
