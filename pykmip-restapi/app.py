import logging
import os
from flask import Flask, jsonify, request
from prometheus_flask_exporter import PrometheusMetrics
from config import AppConfig
from routes.kmip_routes import KMIPRoutes
from routes.barbican_routes import BarbicanRoutes
from services.kmip_service import KMIPService
from services.barbican_service import BarbicanService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_app(config: AppConfig = None) -> Flask:
    if config is None:
        config = AppConfig.from_env()

    app = Flask(__name__)
    PrometheusMetrics(app)

    @app.route('/healthz')
    def healthz():
        return jsonify({"status": "ok"})

    @app.after_request
    def log_request(response):
        logger.info(
            "%s %s %s -> %d",
            request.method,
            request.path,
            request.remote_addr,
            response.status_code
        )
        return response

    kmip_service = KMIPService(config.kmip_db)
    barbican_service = BarbicanService(config.barbican_db)

    kmip_routes = KMIPRoutes(kmip_service)
    barbican_routes = BarbicanRoutes(barbican_service)

    app.register_blueprint(kmip_routes.bp, url_prefix='/kmip')
    app.register_blueprint(barbican_routes.bp, url_prefix='/barbican')

    logger.info("Application created, routes registered.")
    return app


if __name__ == "__main__":
    config = AppConfig.from_env()
    app = create_app(config)
    app.run(host=config.host, port=config.port, debug=config.debug)
