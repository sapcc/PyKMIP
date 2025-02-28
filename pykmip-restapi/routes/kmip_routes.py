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
        self.bp.route('/update_owner', methods=['POST'])(self.update_owner)

    def get_barbican_id(self):
        """
        Retrieves Barbican ID for a given KMIP ID.

        Returns:
            JSON response with Barbican ID or error message.
        """
        kmip_id = request.args.get('kmip_id')
        if not kmip_id:
            return jsonify({"error": "Missing kmip_id"}), 400
        result = self.kmip_service.execute_mysql_queries(kmip_id)
        return jsonify(result)

    def update_policy(self):
        """
        Updates the operation policy name for a KMIP object.

        Returns:
            JSON response indicating success or failure of the update.
        """
        data = request.get_json()

        # Validate input data
        kmip_id = data.get('kmip_id')
        operation_policy_name = data.get('operation_policy_name')

        if not kmip_id or not operation_policy_name:
            return jsonify({"error": "Missing required parameters: 'kmip_id' and 'operation_policy_name'"}), 400

        # Call the KMIPService to execute the update
        try:
            result = self.kmip_service.execute_mysql_queries(kmip_id, operation_policy_name=operation_policy_name)

            # Check for errors in the result
            if "error" in result:
                return jsonify({"error": result["error"]}), 500

            return jsonify({
                "message": "Operation policy updated successfully",
                "kmip_id": kmip_id,
                "updated_policy": operation_policy_name,
                "details": result
            }), 200

        except Exception as e:
            return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    def register_kmip(self):
        """
        Registers a new KMIP object with the provided URL, owner, and policy.

        Returns:
            JSON response indicating success or failure of the registration.
        """
        data = request.get_json()
        url = data.get('url')
        owner = data.get('owner')
        policy = data.get('policy')
        if not url or not owner or not policy:
            return jsonify({"error": "Missing parameters"}), 400
        result = self.kmip_service.register_kmip_object(url, owner, policy)
        return jsonify(result)

    def get_kmip_id_from_barbican(self):
        """
        Retrieves the KMIP ID based on the provided Barbican ID.

        Args:
            barbican_id (str): The unique identifier of the Barbican object.

        Returns:
            JSON response with the KMIP ID or an error message if not found.
        """
        barbican_id = request.args.get('barbican_id')
        if not barbican_id:
            return jsonify({"error": "Missing barbican_id"}), 400
        result = self.kmip_service.get_kmip_id_from_barbican(barbican_id)
        return jsonify(result)

    def update_owner(self):
        """
        Updates the owner of a KMIP object.

        Returns:
            JSON response indicating success or failure of the update.
        """
        data = request.get_json()
        kmip_id = data.get('kmip_id')
        new_owner = data.get('new_owner')

        if not kmip_id or not new_owner:
            return jsonify({"error": "Missing required parameters: 'kmip_id' and 'new_owner'"}), 400

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
            return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
