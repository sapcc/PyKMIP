import os
import mysql.connector
from mysql.connector import Error
import logging

logger = logging.getLogger(__name__)

class BarbicanService:
    """
    A service class to interact with the Barbican database.
    Provides methods to retrieve and update metadata.
    """

    def __init__(self, db_config):
        """
        Initializes the BarbicanService with the given database configuration.

        Args:
            db_config (dict): A dictionary containing database connection parameters.
        """
        self.db_config = db_config
        self.connection = None
        self.cursor = None

    def connect(self):
        """
        Establishes a connection to the database if not already connected.

        Returns:
            A database cursor object.
        """
        if not self.connection or not self.connection.is_connected():
            try:
                self.connection = mysql.connector.connect(**self.db_config)
                self.cursor = self.connection.cursor(dictionary=True)
                logger.info("Database connection established.")
            except Error as e:
                logger.error(f"Failed to connect to the database: {e}")
                raise e
        return self.cursor

    def get_metadata_from_uuid(self, uuid):
        """
        Retrieves metadata from the database using the given UUID.

        Args:
            uuid (str): The unique identifier to search for in the database.

        Returns:
            dict: A dictionary containing either the retrieved metadata or an error message.
                - If successful, returns a dictionary with key "data" and value being a list of dictionaries representing the retrieved metadata.
                - If no metadata is found for the given UUID, returns a dictionary with key "error" and value "No metadata found for the given UUID".
                - If there's a database error, returns a dictionary with key "error" and value containing the error message.
        """
        try:
            cursor = self.connect()
            query = """
                SELECT
                    s.id,
                    s.name,
                    s.algorithm,
                    s.bit_length,
                    s.mode,
                    s.secret_type,
                    s.status,
                    s.created_at,
                    s.updated_at,
                    s.deleted,
                    s.deleted_at,
                    s.expiration,
                    s.creator_id,
                    COALESCE(p.external_id, s.project_id) AS project_id
                FROM secrets s
                LEFT JOIN projects p ON s.project_id = p.id
                WHERE s.id = %s
            """
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

    def update_project_id(self, secret_id, external_id):
        """
        Updates the project_id in the secrets table using the given secret_id and external_id.

        Args:
            secret_id (str): The unique identifier of the secret to update.
            external_id (str): The external identifier of the project.

        Returns:
            dict: A dictionary containing the update result or an error message.
                - If successful, returns a dictionary with key "message" and value "Project ID updated successfully".
                - If no project is found with the given external_id, returns a dictionary with key "error".
                - If no secret is found with the given secret_id, returns a dictionary with key "error".
                - If there's a database error, returns a dictionary with key "error" and value containing the error message.
        """
        try:
            cursor = self.connect()

            # Find the project_id using the external_id
            find_project_query = "SELECT id FROM projects WHERE external_id=%s"
            logger.debug("Executing find query for projects table with placeholders for sensitive data.")
            cursor.execute(find_project_query, (external_id,))
            project = cursor.fetchone()

            if not project:
                return {"error": f"No project found with the given external_id: {external_id}"}

            # Convert bytearray fields to strings (if any)
            project = {key: value.decode('utf-8') if isinstance(value, bytearray) else value for key, value in project.items()}
            project_id = project['id']

            # Update the project_id in the secrets table
            update_query = "UPDATE secrets SET project_id=%s WHERE id=%s"
            logger.debug("Executing update query for secrets table with placeholders for sensitive data.")
            cursor.execute(update_query, (project_id, secret_id))

            if cursor.rowcount == 0:
                return {"error": f"No secret found with the given secret_id: {secret_id}"}

            # Commit the transaction
            self.connection.commit()
            logger.info("Project ID updated successfully for a secret.")

            return {"message": "Project ID updated successfully"}
        except Error as e:
            logger.error(f"Database error: {e}", exc_info=True)
            return {"error": f"Database error: {str(e)}"}
