import os


class Config:
    """
    Set Flask configuration vars.
    """
    # General Config
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JSONIFY_PRETTYPRINT_REGULAR = True
    # Cookies lifetime is 1800 sek (30 min).
    # PERMANENT_SESSION_LIFETIME = 1800

    # Database Config
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Custom Config
    USER_DEFAULT_PASS = os.environ.get('USER_DEFAULT_PASS')

    # Email config
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT')
    MAIL_SECURITY = 'tls'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
