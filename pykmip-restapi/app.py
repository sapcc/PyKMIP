from flask import Flask
from config import AppConfig
from routes.kmip_routes import KMIPRoutes
from routes.barbican_routes import BarbicanRoutes
from services.kmip_service import KMIPService
from services.barbican_service import BarbicanService

def create_app(config: AppConfig = None) -> Flask:
    # Load config from environment if not provided
    if config is None:
        config = AppConfig.from_env()

    # Create Flask app
    app = Flask(__name__)

    # Initialize services
    kmip_service = KMIPService(config.kmip_db)
    barbican_service = BarbicanService(config.barbican_db)

    # Initialize and register route blueprints with prefixes
    kmip_routes = KMIPRoutes(kmip_service)
    barbican_routes = BarbicanRoutes(barbican_service)

    # Register blueprints with appropriate prefixes
    app.register_blueprint(kmip_routes.bp, url_prefix='/kmip')
    app.register_blueprint(barbican_routes.bp, url_prefix='/barbican')

    return app

if __name__ == "__main__":
    # Load config from environment variables
    config = AppConfig.from_env()

    # Create and run the Flask app
    app = create_app(config)
    app.run(host=config.host, port=config.port, debug=config.debug)
