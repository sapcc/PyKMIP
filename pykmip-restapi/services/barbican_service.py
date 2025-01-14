import os
import mysql.connector
from mysql.connector import Error
import logging

logger = logging.getLogger(__name__)

class BarbicanService:
    def __init__(self, db_config):
        self.db_config = db_config

    def get_metadata_from_uuid(self, uuid):
        try:
            # Establish the database connection
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM secrets WHERE id = %s"
                logger.debug(f"Executing query: {query} with uuid={uuid}")
                cursor.execute(query, (uuid,))
                result = cursor.fetchall()

                # Convert bytearray fields to strings
                for row in result:
                    for key, value in row.items():
                        if isinstance(value, bytearray):
                            row[key] = value.decode('utf-8')

                if result:
                    return {"data": result}
                else:
                    return {"error": "No metadata found for the given UUID"}
        except Error as e:
            logger.error(f"Database error: {e}", exc_info=True)
            return {"error": f"Database error: {str(e)}"}
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def update_project_id(self, secret_id, external_id):
        try:
            # Establish the database connection
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)

                # Find the project_id using the external_id
                find_project_query = "SELECT id FROM projects WHERE external_id=%s"
                logger.debug(f"Executing query: {find_project_query} with external_id={external_id}")
                cursor.execute(find_project_query, (external_id,))
                project = cursor.fetchone()

                if not project:
                    return {"error": f"No project found with the given external_id: {external_id}"}

                # Convert bytearray fields to strings (if any)
                project = {key: value.decode('utf-8') if isinstance(value, bytearray) else value for key, value in project.items()}

                project_id = project['id']

                # Update the project_id in the secrets table
                update_query = "UPDATE secrets SET project_id=%s WHERE id=%s"
                logger.debug(f"Executing query: {update_query} with project_id={project_id}, secret_id={secret_id}")
                cursor.execute(update_query, (project_id, secret_id))

                if cursor.rowcount == 0:
                    return {"error": f"No secret found with the given secret_id: {secret_id}"}

                # Commit the transaction
                connection.commit()
                logger.info(f"Project ID updated successfully for secret_id={secret_id}")

                return {"message": "Project ID updated successfully"}

        except Error as e:
            logger.error(f"Database error: {e}", exc_info=True)
            return {"error": f"Database error: {str(e)}"}

        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
