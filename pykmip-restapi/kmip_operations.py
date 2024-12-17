from utils import connect_to_db, decode_if_bytes
import time
import logging

logger = logging.getLogger(__name__)

def execute_mysql_queries(kmip_id, mariadb_config, operation_policy_name=None, owner=None):
    connection = connect_to_db(**mariadb_config)

    if not connection:
        return {"error": "Unable to connect to the database"}

    try:
        cursor = connection.cursor(dictionary=True)

        # Fetch the record to confirm the `kmip_id` exists
        select_query = "SELECT * FROM managed_objects WHERE uid=%s"
        logger.debug(f"Executing SELECT query: {select_query} with uid={kmip_id}")
        cursor.execute(select_query, (kmip_id,))
        result = cursor.fetchone()

        if not result:
            return {"error": "No data found for the given uid"}

        # Decode all bytes fields into strings
        result = {key: decode_if_bytes(value) for key, value in result.items()}

        # Extract `barbican_id` from the `value` column
        barbican_url = result.get("value", "")
        if barbican_url:
            barbican_id = barbican_url.split('/')[-1]  # Extract last part of the URL
        else:
            barbican_id = None

        # Prepare and execute the update query if needed
        update_query = None
        if operation_policy_name:
            update_query = "UPDATE managed_objects SET operation_policy_name=%s WHERE uid=%s"
            update_values = (operation_policy_name, kmip_id)
        elif owner:
            update_query = "UPDATE managed_objects SET owner=%s WHERE uid=%s"
            update_values = (owner, kmip_id)

        if update_query:
            logger.debug(f"Executing UPDATE query: {update_query} with values {update_values}")
            cursor.execute(update_query, update_values)
            connection.commit()  # Commit the transaction
            logger.debug("Update operation committed successfully.")

        return {
            "barbican_id": barbican_id,
            "kmip_details": result
        }

    except mysql.connector.Error as e:
        logger.error(f"Database error: {e}")
        return {"error": "Database operation failed"}

    finally:
        if connection.is_connected():
            connection.close()


def get_kmip_id_from_barbican(barbican_id, mariadb_config):
    connection = connect_to_db(**mariadb_config)

    if not connection:
        return {"error": "Unable to connect to the database"}

    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT uid FROM managed_objects WHERE value LIKE %s"
        value_pattern = f"%/{barbican_id}"  # Match URLs ending with the Barbican ID
        cursor.execute(query, (value_pattern,))
        result = cursor.fetchone()

        if not result:
            return {"error": "No KMIP ID found for the given Barbican ID"}

        return {"kmip_id": result["uid"]}

    finally:
        if connection.is_connected():
            connection.close()

def register_kmip_object(url, owner, policy, mariadb_config):
    connection = connect_to_db(**mariadb_config)

    if not connection:
        return {"error": "Unable to connect to the database"}

    try:
        cursor = connection.cursor(dictionary=True)

        # Generate new UID
        cursor.execute("SELECT MAX(uid) AS uid FROM managed_objects")
        max_uid_row = cursor.fetchone()
        new_uuid = (max_uid_row['uid'] or 0) + 1  # Increment UID

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
            new_uuid,  # Use the new UID explicitly
            2,  # object_type (e.g., SymmetricKey)
            'SymmetricKey',  # class_type
            url,  # value
            1,  # name_index
            policy,  # operation_policy_name
            0,  # sensitive
            tstamp,  # initial_date
            owner  # owner
        )
        cursor.execute(insert_managed_objects, managed_objects_values)

        # Insert into crypto_objects table
        insert_crypto_objects = """
        INSERT INTO crypto_objects (uid, cryptographic_usage_mask, state)
        VALUES (%s, %s, %s)
        """
        crypto_objects_values = (new_uuid, 12, 2)  # Use the same UID
        cursor.execute(insert_crypto_objects, crypto_objects_values)

        # Commit the transaction
        connection.commit()

        return {"message": "KMIP object registered successfully", "uid": new_uuid}

    except mysql.connector.Error as e:
        logger.error(f"Error during KMIP registration: {e}")
        return {"error": "KMIP registration failed"}

    finally:
        if connection.is_connected():
            connection.close()
