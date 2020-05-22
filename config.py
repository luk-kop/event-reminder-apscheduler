import os
from pathlib import Path


class Config:
    """
    Set Flask configuration vars.
    """
    # General Config
    SECRET_KEY = os.environ.get('SECRET_KEY')
    # If LOGIN_DISABLED = True - it globally turn off authentication (when unit testing)
    LOGIN_DISABLED = os.environ.get('LOGIN_DISABLED') or False
    JSONIFY_PRETTYPRINT_REGULAR = True
    BASE_DIR = Path(__file__).resolve().parent
    LOGS_DIR = BASE_DIR.joinpath('logs')
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
    # Cookies lifetime is 1800 sek (30 min).
    PERMANENT_SESSION_LIFETIME = 1800

    # Database Config
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Custom Config
    USER_DEFAULT_PASS = os.environ.get('USER_DEFAULT_PASS')
    NOTIFICATION_SERVICE_STATUS = False

    # Email config
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT')
    MAIL_SECURITY = 'tls'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
