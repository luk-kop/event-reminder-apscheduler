# Standard library imports
import logging
import os
from logging.handlers import RotatingFileHandler

# Third party imports
from flask import Flask
from elasticsearch import Elasticsearch

# Local app imports
from config import Config
from reminder.main import main
from reminder.auth import auth
from reminder.admin import admin
from reminder.extensions import (
    db,
    login_manager,
    csrf,
    migrate,
    scheduler,
)
from reminder.custom_handler import DatabaseHandler
from reminder.models import Event


def create_app():
    """
    Construct the core app object.
    """
    app = Flask(__name__)
    # Application Configuration
    app.config.from_object(Config)
    with app.app_context():
        register_extensions(app)
        register_blueprints(app)
        configure_logger(app)
        return app


def register_extensions(app):
    """
    Register Flask extensions.
    """
    # Initialize Plugins
    # create SQLAlchemy instance:
    db.init_app(app)
    # enable CSRF protection globally for Flask app
    csrf.init_app(app)
    # 'migrate' object represents the migration engine
    migrate.init_app(app, db)
    # use for user log in
    login_manager.init_app(app)
    # tell login_manager where cane find login page (here 'login' function)
    login_manager.login_view = 'auth_bp.login'
    login_manager.login_message_category = 'info'
    # initialize apscheduler obj for background task
    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()
    # initialize ElasticSearch
    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) if app.config['ELASTICSEARCH_URL'] else None


def register_blueprints(app):
    """
    Register Flask blueprints.
    """
    app.register_blueprint(main.main_bp)
    app.register_blueprint(auth.auth_bp, url_prefix='/auth')
    app.register_blueprint(admin.admin_bp, url_prefix='/admin')


def configure_logger(app):
    """
    Configure loggers.
    """
    # logging service dir
    logs_dir = app.config['LOGS_DIR']
    if not os.path.exists(logs_dir):
        os.mkdir(logs_dir)

    # create dedicated loggers
    app.logger_general = logging.getLogger("main")
    my_formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S')
    file_handler = RotatingFileHandler(f'{logs_dir}/app.log', maxBytes=30720, backupCount=5)
    file_handler.setFormatter(my_formatter)
    app.logger_general.addHandler(file_handler)
    app.logger_general.setLevel(logging.DEBUG)

    app.logger_general.addHandler((DatabaseHandler(db.session)))

    # customized logger attached to the application is convenient because anywhere in the application I can use current_app.logger.. to access it.
    # auth logger
    app.logger_auth = logging.getLogger("auth")
    file_handler_auth = RotatingFileHandler(f'{logs_dir}/auth.log', maxBytes=30720, backupCount=5)
    file_handler_auth.setFormatter(my_formatter)
    app.logger_auth.setLevel(logging.DEBUG)
    app.logger_auth.addHandler(file_handler_auth)

    app.logger_auth.addHandler((DatabaseHandler(db.session)))

    # admin logger
    app.logger_admin = logging.getLogger("admin")
    file_handler_admin = RotatingFileHandler(f'{logs_dir}/admin.log', maxBytes=30720, backupCount=5)
    file_handler_admin.setFormatter(my_formatter)
    app.logger_admin.setLevel(logging.DEBUG)
    app.logger_admin.addHandler(file_handler_admin)
    app.logger_admin.addHandler((DatabaseHandler(db.session)))

    app.logger_general.info('Reminder App startup')
