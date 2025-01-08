from flask import Flask
from config import Config
from flask_cors import CORS
import logging

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure logging
    logging.basicConfig(filename='app.log', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    # Enable CORS for all origins (for development purposes)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from app.routes import bp as routes_bp
    app.register_blueprint(routes_bp, url_prefix='/api')

    return app