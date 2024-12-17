from utils import connect_to_db
import logging

logger = logging.getLogger(__name__)

def get_metadata_from_uuid(uuid, barbican_db_config):
    """
    Fetch metadata for a given Barbican UUID from the secrets table.
    """
    connection = connect_to_db(**barbican_db_config)

    if not connection:
        return {"error": "Unable to connect to the Barbican database"}

    try:
        cursor = connection.cursor(dictionary=True)

        # Query to fetch metadata for the given UUID
        query = "SELECT * FROM secrets WHERE id=%s"
        logger.debug(f"Executing query: {query} with uuid={uuid}")
        cursor.execute(query, (uuid,))
        result = cursor.fetchone()

        if not result:
            return {"error": "No metadata found for the given UUID"}

        return {"metadata": result}

    except Exception as e:
        logger.error(f"Error fetching metadata: {e}")
        return {"error": "Error fetching metadata from the database"}

    finally:
        if connection.is_connected():
            connection.close()


def update_project_id(secret_id, external_id, barbican_db_config):
    connection = connect_to_db(**barbican_db_config)

    if not connection:
        return {"error": "Unable to connect to the Barbican database"}

    try:
        cursor = connection.cursor(dictionary=True)

        # Find the project_id using the external_id
        find_project_query = "SELECT id FROM projects WHERE external_id=%s"
        cursor.execute(find_project_query, (external_id,))
        project = cursor.fetchone()

        if not project:
            return {"error": f"No project found with the given external_id: {external_id}"}

        project_id = project['id']

        # Update the project_id in the secrets table
        update_query = "UPDATE secrets SET project_id=%s WHERE id=%s"
        logger.debug(f"Executing query: {update_query} with project_id={project_id}, secret_id={secret_id}")
        cursor.execute(update_query, (project_id, secret_id))

        if cursor.rowcount == 0:
            return {"error": f"No secret found with the given secret_id: {secret_id}"}

        connection.commit()

        return {"message": "Project ID updated successfully"}

    except Exception as e:
        logger.error(f"Error updating project_id: {e}", exc_info=True)
        return {"error": f"Database error: {str(e)}"}

    finally:
        if connection.is_connected():
            connection.close()

