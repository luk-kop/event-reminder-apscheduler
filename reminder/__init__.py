from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from apscheduler.schedulers.background import BackgroundScheduler
from flask_wtf.csrf import CSRFProtect

# from flask_bcrypt import Bcrypt
# from flask_mail import Mail

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()
scheduler = BackgroundScheduler()


def create_app():
    """
    Construct the core app object.
    """
    app = Flask(__name__)

    # Application Configuration
    app.config.from_object(Config)

    # Create SQLAlchemy instance:
    db.init_app(app)
    # enable CSRF protection globally for Flask app
    csrf.init_app(app)
    # Initialize Pluginsfrom reminder import routes, models

    # 'migrate' object represents the migration engine
    migrate.init_app(app, db)
    # use to hash passwords bcrypt = Bcrypt(app)
    # use for user log in
    login_manager.init_app(app)
    # tell login_manager where cane find login page (here 'login' function)
    login_manager.login_view = 'auth_bp.login'
    login_manager.login_message_category = 'info'       # login message

    # create apscheduler obj for background task
    if not scheduler.running:
        scheduler.start(app)

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