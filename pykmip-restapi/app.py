
from flask import Flask
from config import AppConfig
from routes.kmip_routes import KMIPRoutes
from routes.barbican_routes import BarbicanRoutes
from services.kmip_service import KMIPService
from services.barbican_service import BarbicanService

def create_app(config: AppConfig = None) -> Flask:
    if config is None:
        config = AppConfig.from_env()

    app = Flask(__name__)

    # Initialize services
    kmip_service = KMIPService(config.kmip_db)
    barbican_service = BarbicanService(config.barbican_db)

    # Initialize and register route blueprints
    kmip_routes = KMIPRoutes(kmip_service)
    barbican_routes = BarbicanRoutes(barbican_service)

    app.register_blueprint(kmip_routes.bp, url_prefix='/kmip')
    app.register_blueprint(barbican_routes.bp, url_prefix='/barbican')

    return app

if __name__ == "__main__":
    config = AppConfig.from_env()
    app = create_app(config)
    app.run(host=config.host, port=config.port, debug=config.debug)
