
import os

class AppConfig:
    def __init__(self, kmip_db, barbican_db, host, port, debug):
        self.kmip_db = kmip_db
        self.barbican_db = barbican_db
        self.host = host
        self.port = port
        self.debug = debug

    @classmethod
    def from_env(cls):
        return cls(
            kmip_db={
                "host": os.getenv('KMIP_MARIADB_SERVICE_HOST', 'localhost'),
                "port": int(os.getenv('KMIP_MARIADB_SERVICE_PORT', 3306)),
                "user": os.getenv('KMIP_MARIADB_SERVICE_USER', 'root'),
                "password": os.getenv('KMIP_MARIADB_SERVICE_PASSWORD', ''),
                "database": os.getenv('KMIP_MARIADB_NAME', 'kmip'),
            },
            barbican_db={
                "host": os.getenv('BARBICAN_MARIADB_SERVICE_HOST', 'localhost'),
                "port": int(os.getenv('BARBICAN_MARIADB_SERVICE_PORT', 3306)),
                "user": os.getenv('BARBICAN_MARIADB_SERVICE_USER', 'root'),
                "password": os.getenv('BARBICAN_MARIADB_SERVICE_PASSWORD', ''),
                "database": os.getenv('BARBICAN_MARIADB_NAME', 'barbican'),
            },
            host=os.getenv('APP_HOST', '0.0.0.0'),
            port=int(os.getenv('APP_PORT', 5006)),
            debug=bool(os.getenv('APP_DEBUG', False))
        )
