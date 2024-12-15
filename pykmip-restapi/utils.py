import logging
import mysql.connector
import time

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def connect_to_db(host, port, user, password, database):
    retries = 3
    for i in range(retries):
        try:
            connection = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
            logger.debug("Database connection successful!")
            return connection
        except mysql.connector.Error as e:
            logger.error(f"Database connection failed: {e}")
            time.sleep(2)
    return None

def decode_if_bytes(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value
