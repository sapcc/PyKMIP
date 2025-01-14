import mysql.connector
from mysql.connector import Error
import time
import logging

logger = logging.getLogger(__name__)

class KMIPService:
    def __init__(self, db_config):
        self.db_config = db_config

    def execute_mysql_queries(self, kmip_id, operation_policy_name=None, owner=None):
        try:
            # Establish the database connection
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)

                # SELECT Query
                select_query = "SELECT * FROM managed_objects WHERE uid=%s"
                logger.debug(f"Executing SELECT query: {select_query} with values ({kmip_id},)")
                cursor.execute(select_query, (kmip_id,))
                result = cursor.fetchone()

                if not result:
                    return {"error": "No data found for the given uid"}

                # Convert bytearray fields to strings
                result = {key: value.decode('utf-8') if isinstance(value, bytearray) else value for key, value in result.items()}

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
                    connection.commit()
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

        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def register_kmip_object(self, url, owner, policy):
        try:
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)

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
                connection.commit()

                return {"message": "KMIP object registered successfully", "uid": new_uuid}

        except Error as e:
            logger.error(f"Error during KMIP registration: {e}")
            return {"error": f"KMIP registration failed: {str(e)}"}

        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def get_kmip_id_from_barbican(self, barbican_id):
        try:
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                query = "SELECT uid FROM managed_objects WHERE value LIKE %s"
                value_pattern = f"%/{barbican_id}"
                cursor.execute(query, (value_pattern,))
                result = cursor.fetchone()

                if not result:
                    return {"error": "No KMIP ID found for the given Barbican ID"}

                kmip_id = result["uid"]
                if isinstance(kmip_id, bytearray):
                    kmip_id = kmip_id.decode('utf-8')

                return {"kmip_id": kmip_id}

        except Error as e:
            logger.error(f"Database error: {e}")
            return {"error": f"Database operation failed: {str(e)}"}

        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
