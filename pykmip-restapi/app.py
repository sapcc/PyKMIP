from flask import Flask, jsonify, request
from kmip_operations import execute_mysql_queries, get_kmip_id_from_barbican, register_kmip_object
from barbican_operations import get_metadata_from_uuid, update_project_id
import os

app = Flask(__name__)

# KMIP Database configuration
kmip_db_config = {
    "host": os.getenv('KMIP_MARIADB_SERVICE_HOST', 'localhost'),
    "port": int(os.getenv('KMIP_MARIADB_SERVICE_PORT', 3306)),
    "user": os.getenv('KMIP_MARIADB_SERVICE_USER', 'root'),
    "password": os.getenv('KMIP_MARIADB_SERVICE_PASSWORD', ''),
    "database": os.getenv('KMIP_MARIADB_NAME', 'kmip'),
}

# Barbican Database configuration
barbican_db_config = {
    "host": os.getenv('BARBICAN_MARIADB_SERVICE_HOST', 'localhost'),
    "port": int(os.getenv('BARBICAN_MARIADB_SERVICE_PORT', 3306)),
    "user": os.getenv('BARBICAN_MARIADB_SERVICE_USER', 'root'),
    "password": os.getenv('BARBICAN_MARIADB_SERVICE_PASSWORD', ''),
    "database": os.getenv('BARBICAN_MARIADB_NAME', 'barbican'),
}

# Route 1: Get Barbican ID
@app.route('/get_barbican_id', methods=['GET'])
def get_barbican_id():
    kmip_id = request.args.get('kmip_id')

    if not kmip_id:
        return jsonify({"error": "Missing kmip_id"}), 400

    result = execute_mysql_queries(kmip_id, kmip_db_config)
    if "error" in result:
        return jsonify(result), 500

    return jsonify({"barbican_id": result.get("barbican_id")})

# Route 2: Get KMIP ID
@app.route('/get_kmip_id', methods=['GET'])
def get_kmip_id():
    barbican_id = request.args.get('barbican_id')

    if not barbican_id:
        return jsonify({"error": "Missing barbican_id"}), 400

    result = get_kmip_id_from_barbican(barbican_id, kmip_db_config)
    if "error" in result:
        return jsonify(result), 500

    return jsonify({"kmip_id": result["kmip_id"]})

# Route 3: Get KMIP Details
@app.route('/get_kmip_details', methods=['GET'])
def get_kmip_details():
    kmip_id = request.args.get('kmip_id')

    if not kmip_id:
        return jsonify({"error": "Missing kmip_id"}), 400

    result = execute_mysql_queries(kmip_id, kmip_db_config)
    if "error" in result:
        return jsonify(result), 500

    return jsonify({
        "barbican_id": result.get("barbican_id"),
        "kmip_details": result["kmip_details"]
    })

# Route 4: Update Policy
@app.route('/update_policy', methods=['POST'])
def update_policy():
    data = request.get_json()
    kmip_id = data.get('kmip_id')
    operation_policy_name = data.get('operation_policy_name')

    if not kmip_id or not operation_policy_name:
        return jsonify({"error": "Missing kmip_id or operation_policy_name"}), 400

    result = execute_mysql_queries(kmip_id, kmip_db_config, operation_policy_name=operation_policy_name)
    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)

# Route 5: Update Owner
@app.route('/update_owner', methods=['POST'])
def update_owner():
    data = request.get_json()
    kmip_id = data.get('kmip_id')
    owner = data.get('owner')

    if not kmip_id or not owner:
        return jsonify({"error": "Missing kmip_id or owner"}), 400

    result = execute_mysql_queries(kmip_id, kmip_db_config, owner=owner)
    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)

# Route 6: KMIP Register
@app.route('/kmip_register', methods=['POST'])
def kmip_register():
    data = request.get_json()
    url = data.get('url')
    owner = data.get('owner')
    policy = data.get('policy')

    if not url or not owner or not policy:
        return jsonify({"error": "Missing url, owner, or policy"}), 400

    result = register_kmip_object(url, owner, policy, kmip_db_config)
    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)

# Barbican API Section
# Route 1 : Get Metadata
@app.route('/get_barbican_metadata', methods=['GET'])
def get_metadata():
    uuid = request.args.get('uuid')

    if not uuid:
        return jsonify({"error": "Missing uuid"}), 400

    result = get_metadata_from_uuid(uuid, barbican_db_config)
    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)

# Route 2 : Update Project ID
@app.route('/update_project_id', methods=['POST'])
def update_project_id_api():
    data = request.get_json()
    secret_id = data.get('secret_id')
    project_id = data.get('project_id')

    if not secret_id or not project_id:
        return jsonify({"error": "Missing secret_id or project_id"}), 400

    result = update_project_id(secret_id, project_id, barbican_db_config)
    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)
