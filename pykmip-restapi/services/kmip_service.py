import mysql.connector
from mysql.connector import Error
import time
import logging

logger = logging.getLogger(__name__)

class KMIPService:
    """
    A service class to interact with the KMIP database.
    Provides methods to retrieve and update KMIP objects.
    """

    def __init__(self, db_config):
        """
        Initializes the KMIPService with the given database configuration.

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

    @staticmethod
    def decode_result(result):
        """
        Decodes bytes in a result dictionary into strings.

        Args:
            result (dict): The result dictionary from the database query.

        Returns:
            dict: The decoded dictionary.
        """
        if result:
            return {k: (v.decode('utf-8') if isinstance(v, (bytes, bytearray)) else v) for k, v in result.items()}
        return result

    def execute_mysql_queries(self, kmip_id, operation_policy_name=None, owner=None):
        """
        Executes SQL queries on the KMIP database to retrieve and update KMIP objects.

        Args:
            kmip_id (str): The unique identifier of the KMIP object.
            operation_policy_name (str, optional): The operation policy to update.
            owner (str, optional): The owner to update.

        Returns:
            dict: A dictionary containing the KMIP object details or an error message.
        """
        try:
            cursor = self.connect()

            # SELECT Query
            select_query = "SELECT * FROM managed_objects WHERE uid=%s"
            logger.debug(f"Executing SELECT query: {select_query} with values ({kmip_id},)")
            cursor.execute(select_query, (kmip_id,))
            result = cursor.fetchone()

            if not result:
                return {"error": "No data found for the given uid"}

            # Decode the result
            result = self.decode_result(result)

            # Extract Barbican ID from the URL
            barbican_url = result.get("value", "")
            barbican_id = barbican_url.split('/')[-1] if barbican_url else None

            # Prepare and execute the UPDATE query if needed
            update_query = None
            update_values = None
            if operation_policy_name:
                update_query = "UPDATE managed_objects SET operation_policy_name=%s WHERE uid=%s"
                update_values = (operation_policy_name, kmip_id)
            elif owner:
                update_query = "UPDATE managed_objects SET owner=%s WHERE uid=%s"
                update_values = (owner, kmip_id)

            if update_query:
                logger.debug(f"Executing UPDATE query: {update_query} with values {update_values}")
                cursor.execute(update_query, update_values)
                self.connection.commit()
                logger.debug("Update operation committed successfully.")

            return {
                "barbican_id": barbican_id,
                "kmip_details": result,
                "query_executed": update_query,
                "query_values": update_values
            }

        except Error as e:
            logger.error(f"Database error: {e}")
            return {"error": f"Database operation failed: {str(e)}"}

    def register_kmip_object(self, url, owner, policy):
        """
        Registers a new KMIP object in the managed_objects table.

        Args:
            url (str): The URL of the KMIP object.
            owner (str): The owner of the KMIP object.
            policy (str): The policy to apply to the KMIP object.

        Returns:
            dict: A dictionary containing the registration result or an error message.
        """
        try:
            cursor = self.connect()

            # Generate new UID
            cursor.execute("SELECT MAX(uid) AS uid FROM managed_objects")
            max_uid_row = cursor.fetchone()
            new_uuid = (max_uid_row['uid'] or 0) + 1

            # Get current timestamp
            tstamp = int(time.time())

            # Insert into managed_objects table
            insert_managed_objects = """
            INSERT INTO managed_objects (
                uid, object_type, class_type, value, name_index,
                operation_policy_name, `sensitive`, initial_date, owner
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            managed_objects_values = (
                new_uuid, 2, 'SymmetricKey', url, 1, policy, 0, tstamp, owner
            )
            cursor.execute(insert_managed_objects, managed_objects_values)

            # Insert into crypto_objects table
            insert_crypto_objects = """
            INSERT INTO crypto_objects (uid, cryptographic_usage_mask, state)
            VALUES (%s, %s, %s)
            """
            crypto_objects_values = (new_uuid, 12, 2)
            cursor.execute(insert_crypto_objects, crypto_objects_values)

            # Insert into keys table
            insert_keys = """
            INSERT INTO `keys` (
                uid, cryptographic_algorithm, cryptographic_length, key_format_type,
                _kdw_wrapping_method, _kdw_eki_cp_block_cipher_mode, _kdw_eki_cp_padding_method,
                _kdw_eki_cp_hashing_algorithm, _kdw_eki_cp_key_role_type,
                _kdw_eki_cp_digital_signature_algorithm, _kdw_eki_cp_cryptographic_algorithm,
                _kdw_mski_cp_block_cipher_mode, _kdw_mski_cp_padding_method,
                _kdw_mski_cp_hashing_algorithm, _kdw_mski_cp_key_role_type,
                _kdw_mski_cp_digital_signature_algorithm, _kdw_mski_cp_cryptographic_algorithm,
                _kdw_encoding_option
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            keys_values = (
                new_uuid, 3, 256, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1
            )
            cursor.execute(insert_keys, keys_values)

            # Insert into symmetric_keys table
            insert_symmetric_keys = """
            INSERT INTO symmetric_keys (uid)
            VALUES (%s)
            """
            cursor.execute(insert_symmetric_keys, (new_uuid,))

            # Commit the transaction
            self.connection.commit()

            return {"message": "KMIP object registered successfully", "uid": new_uuid}

        except Error as e:
            logger.error(f"Error during KMIP registration: {e}")
            return {"error": f"KMIP registration failed: {str(e)}"}

    def get_kmip_id_from_barbican(self, barbican_id):
        """
        Retrieves the KMIP ID based on the provided Barbican ID.

        Args:
            barbican_id (str): The unique Barbican ID to search for.

        Returns:
            dict: A dictionary with the KMIP ID or an error message.
        """
        try:
            query = "SELECT uid FROM managed_objects WHERE value LIKE %s"
            cursor = self.connect()
            cursor.execute(query, (f"%{barbican_id}%",))
            result = cursor.fetchone()

            if not result:
                return {"error": f"No KMIP ID found for Barbican ID: {barbican_id}"}

            # Decode the result and return
            result = self.decode_result(result)
            return {"kmip_id": result.get("uid")}

        except Error as e:
            logger.error(f"Database error while fetching KMIP ID for Barbican ID {barbican_id}: {e}")
            return {"error": f"Database operation failed: {str(e)}"}
