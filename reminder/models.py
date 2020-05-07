from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin

from reminder.extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    """Load user to login"""
    return User.query.get(int(user_id))


# Association Table
user_to_event = db.Table('user_to_event',
                         db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                         db.Column('event_id', db.Integer(), db.ForeignKey('event.id')))


class Role(db.Model):
    """User's roles"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))
    users_id = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return f'{self.name}'


class User(db.Model, UserMixin):
    """Table of users authorized to add new events."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # Events that have been created by user.
    events_created = db.relationship('Event',
                                     backref='author',
                                     lazy='dynamic',
                                     foreign_keys='Event.author_uid')
    events_notified = db.relationship('Event',
                                      secondary=user_to_event,
                                      back_populates='notified_uids')
    # Weather user can login by login page and add new notify records.
    access_granted = db.Column(db.Boolean, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    last_seen = db.Column(db.DateTime)
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    failed_login_attempts = db.Column(db.Integer, default=0)
    pass_change_req = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'{self.username}'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        if self.role.name == 'admin':
            return True

    def user_seen(self):
        self.last_seen = datetime.utcnow()


class AnonymousUser(AnonymousUserMixin):
    def is_admin(self):
        return False


class Event(db.Model):
    """Events that will be notified"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(40), nullable=False)
    details = db.Column(db.String(200))         # zmienić na większa wartosc
    time_creation = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    all_day_event = db.Column(db.Boolean, nullable=False)
    time_event_start = db.Column(db.DateTime, index=True)
    time_event_stop = db.Column(db.DateTime, index=True)
    # Whether to notify or not.
    to_notify = db.Column(db.Boolean, nullable=False)
    time_notify = db.Column(db.DateTime, index=True)
    # Who should be notified.
    # notified_uid = db.Column(db.Integer, db.ForeignKey('user.id'))
    # Who is an author of notify record
    author_uid = db.Column(db.Integer, db.ForeignKey('user.id'))
    # Weather the notification has already been sent.
    notification_sent = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    notified_uids = db.relationship('User',
                                    secondary=user_to_event,
                                    back_populates='events_notified')

    def __repr__(self):
        return f'Event {self.title}'


class Notification(db.Model):
    """Notification service config."""
    id = db.Column(db.Integer, primary_key=True)
    notify_unit = db.Column(db.String(10), unique=True)
    notify_interval = db.Column(db.Integer)


class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_name = db.Column(db.String)
    level = db.Column(db.String) # info, debug, or error?
    msg = db.Column(db.String(100)) # any custom log you may have included
    time = db.Column(db.DateTime) # the current timestamp

    def __init__(self, log_name, level, time, msg):
        self.log_name = log_name
        self.level = level
        self.time = time
        self.msg = msg

    @classmethod
    def delete_expired(cls):
        """Delete logs older than indicated time-frame."""
        expiration_days = 7
        limit = datetime.utcnow() - timedelta(days=expiration_days)
        cls.query.filter(cls.time <= limit).delete
        db.session.commit()