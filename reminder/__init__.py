from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
# from apscheduler.schedulers.background import BackgroundScheduler
from flask_apscheduler import APScheduler
from flask_wtf.csrf import CSRFProtect
# from flask_bcrypt import Bcrypt
import logging
import os
from logging.handlers import RotatingFileHandler
# from redis import Redis
# import rq


db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()
# scheduler = BackgroundScheduler()
scheduler = APScheduler()


def create_app():
    """
    Construct the core app object.
    """
    app = Flask(__name__)

    # Application Configuration
    app.config.from_object(Config)

    # Initialize Plugins
    # Create SQLAlchemy instance:
    db.init_app(app)
    # enable CSRF protection globally for Flask app
    csrf.init_app(app)

    # 'migrate' object represents the migration engine
    migrate.init_app(app, db)

    # use to hash passwords bcrypt = Bcrypt(app)

    # use for user log in
    login_manager.init_app(app)
    # tell login_manager where cane find login page (here 'login' function)
    login_manager.login_view = 'auth_bp.login'
    login_manager.login_message_category = 'info'       # login message

    # logging service config
    logs_dir = app.config['LOGS_DIR']
    if not os.path.exists(logs_dir):
        os.mkdir(logs_dir)
    # default app.logger customization
    my_formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S')
    file_handler= RotatingFileHandler(f'{logs_dir}/app.log', maxBytes=30720, backupCount=5)
    file_handler.setFormatter(my_formatter)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.DEBUG)
    app.logger.info('Reminder App startup')

    # create dedicated loggers
    # customized logger attached to the application is convenient because anywhere in the application I can use current_app.logger.. to access it.
    # auth logger
    app.logger_auth = logging.getLogger("logger1")
    file_handler_auth = RotatingFileHandler(f'{logs_dir}/auth.log', maxBytes=30720, backupCount=5)
    file_handler_auth.setFormatter(my_formatter)
    app.logger_auth.setLevel(logging.DEBUG)
    app.logger_auth.addHandler(file_handler_auth)
    # admin logger
    app.logger_admin = logging.getLogger("admin.auth")
    file_handler_admin = RotatingFileHandler(f'{logs_dir}/admin.log', maxBytes=30720, backupCount=5)
    file_handler_admin.setFormatter(my_formatter)
    app.logger_admin.setLevel(logging.DEBUG)
    app.logger_admin.addHandler(file_handler_admin)

    # redis
    # app.redis = Redis.from_url(app.config['REDIS_URL'])
    # app.task_queue = rq.Queue('reminder-tasks', connection=app.redis)

    # initialize apscheduler obj for background task
    scheduler.init_app(app)
    if not scheduler.running:
        scheduler.start()
        # scheduler.start(app)

    with app.app_context():
        from .main import main
        from .auth import auth
        from .admin import admin

        # Register Blueprints
        app.register_blueprint(main.main_bp)
        app.register_blueprint(auth.auth_bp, url_prefix='/auth')
        app.register_blueprint(admin.admin_bp, url_prefix='/admin')

        # Create db Models
        # db.create_all()
        return app