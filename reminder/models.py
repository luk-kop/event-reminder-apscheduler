from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from sqlalchemy import func

from reminder.extensions import db, login_manager
from reminder.search import add_to_index, remove_from_index, query_index


@login_manager.user_loader
def load_user(user_id):
    """
    Load user to login
    """
    return User.query.get(int(user_id))


class SearchableMixin:
    """
    Class, that when attached to a model, will give it the ability to automatically manage
    an associated full-text index.
    """
    @classmethod
    def search(cls, expression, page, per_page, filter_data=None):
        ids, total = query_index(cls.__tablename__, expression, page, per_page, filter_data)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


# Association Table
user_to_event = db.Table('user_to_event',
                         db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                         db.Column('event_id', db.Integer(), db.ForeignKey('event.id')))


class Role(db.Model):
    """User's roles"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))
    # Role.query.filter(Role.name=="user").first().users_id.all() - return all users
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return f'{self.name}'


class User(UserMixin, db.Model):
    """
    Table of users authorized to add new events.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # Events that have been created by user.
    events_created = db.relationship('Event',
                                     backref='author',
                                     lazy='dynamic',
                                     foreign_keys='Event.author_uid',
                                     cascade='all, delete-orphan')
    events_notified = db.relationship('Event',
                                      secondary=user_to_event,
                                      back_populates='notified_users')
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

    @classmethod
    def get_all_standard_users(cls, sort=True):
        """
        Method provides a list of users with 'user' role.
        """
        if sort:
            users = cls.query.filter(cls.role_id == 2).order_by(func.lower(User.username).asc()).all()
        else:
            users = cls.query.filter(cls.role_id == 2).all()
        return users

    def user_seen(self):
        self.last_seen = datetime.utcnow()


class AnonymousUser(AnonymousUserMixin):
    def is_admin(self):
        return False


class Event(SearchableMixin, db.Model):
    """
    Events that will be notified.
    """
    __searchable__ = ['is_active', 'title', 'details']
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    details = db.Column(db.String(300))
    time_creation = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    all_day_event = db.Column(db.Boolean, nullable=False)
    time_event_start = db.Column(db.DateTime, index=True)
    time_event_stop = db.Column(db.DateTime, index=True)
    # Whether to notify or not.
    to_notify = db.Column(db.Boolean, nullable=False)
    time_notify = db.Column(db.DateTime, index=True, default=None)
    # Who is an author of notify record
    author_uid = db.Column(db.Integer, db.ForeignKey('user.id'))
    # Weather the notification has already been sent.
    notification_sent = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    # Who should be notified.
    notified_users = db.relationship('User',
                                     secondary=user_to_event,
                                     back_populates='events_notified')

    def __repr__(self):
        return f'Event {self.title}'


class Notification(db.Model):
    """
    Notification service config.
    """
    id = db.Column(db.Integer, primary_key=True)
    notify_unit = db.Column(db.String(10), unique=True)
    notify_interval = db.Column(db.Integer)


class Log(SearchableMixin, db.Model):
    __searchable__ = ['msg']
    id = db.Column(db.Integer, primary_key=True)
    log_name = db.Column(db.String(20))
    level = db.Column(db.String(20))
    msg = db.Column(db.String(100))
    time = db.Column(db.DateTime)

    def __init__(self, log_name, level, time, msg):
        self.log_name = log_name
        self.level = level
        self.time = time
        self.msg = msg

    @classmethod
    def delete_expired(cls, expiration_days):
        """
        Delete logs older than indicated time-frame.
        """
        limit = datetime.utcnow() - timedelta(days=expiration_days)
        cls.query.filter(cls.time <= limit).delete()
        db.session.commit()


