#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Table, ForeignKey
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import random
import os
import argparse


def random_user_id():
    """
    Func returns a randomly selected user id from all available users (with role user) in the database.
    """
    random_id = random.choice([id[0] for id in session.query(User.id).filter(User.role_id != 1).all()])
    return random_id


Base = declarative_base()


# Crete Models in db
class Role(Base):
    """User's roles"""
    __tablename__ = 'role'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(255))
    users = relationship('User', backref='role', lazy='dynamic')


# Many-To-Many table
user_to_event = Table('user_to_event',
                      Base.metadata,
                      Column('user_id', Integer(), ForeignKey('user.id')),
                      Column('event_id', Integer(), ForeignKey('event.id')))


class User(Base):
    """Table of users authorized to add new events."""
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(40), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    events_created = relationship('Event',
                                  backref='author',
                                  lazy='dynamic',
                                  foreign_keys='Event.author_uid',
                                  cascade='all, delete-orphan')
    events_notified = relationship('Event',
                                   secondary=user_to_event,
                                   back_populates='notified_users')
    access_granted = Column(Boolean, nullable=False)
    role_id = Column(Integer, ForeignKey('role.id'))
    last_seen = Column(DateTime)
    creation_date = Column(DateTime, default=datetime.utcnow)
    failed_login_attempts = Column(Integer, default=0)
    pass_change_req = Column(Boolean, default=False)


class Event(Base):
    """Events that will be notified"""
    __tablename__ = 'event'
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    details = Column(String(300))
    time_creation = Column(DateTime, index=True, default=datetime.utcnow)
    all_day_event = Column(Boolean, nullable=False)
    time_event_start = Column(DateTime, index=True)
    time_event_stop = Column(DateTime, index=True)
    to_notify = Column(Boolean, nullable=False)
    time_notify = Column(DateTime, index=True, default=None)
    author_uid = Column(Integer, ForeignKey('user.id'))
    notification_sent = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    notified_users = relationship('User',
                                 secondary=user_to_event,
                                 back_populates='events_notified')


class Notification(Base):
    """Notification service config."""
    __tablename__ = 'notification'
    id = Column(Integer, primary_key=True)
    notify_unit = Column(String(10), unique=True)
    notify_interval = Column(Integer)


class Log(Base):
    __tablename__ = 'log'
    id = Column(Integer, primary_key=True)
    log_name = Column(String)
    level = Column(String)
    msg = Column(String(100))
    time = Column(DateTime)

    def __init__(self, log_name, level, time, msg):
        self.log_name = log_name
        self.level = level
        self.time = time
        self.msg = msg


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script adds dummy data to the database')
    parser.add_argument('-u', '--adminuser', default='admin', help='Username for admin account (default: admin)')
    parser.add_argument('-p', '--adminpass', default='admin', help='Password for admin account (default: admin)')
    parser.add_argument('-d', '--dbname', default='app.db', help='Change SQLite\'s db name (default: app.db)')
    args = parser.parse_args()

    db_name = args.dbname
    admin_username = args.adminuser
    admin_passwd = args.adminpass
    # default pass for dummy users
    user_passwd = 'password'

    if os.path.exists(db_name):
        print(f'event-reminder: Removing an existing DB - "{db_name}"...')
        os.remove(db_name)

    engine = create_engine(f'sqlite:///{db_name}')
    # generate database schema
    Base.metadata.create_all(engine)
    DBSession = sessionmaker(bind=engine)

    session = DBSession()

    roles = [
        Role(name='admin'),
        Role(name='user')
    ]

    session.bulk_save_objects(roles)
    session.commit()

    notification_config = [
        Notification(notify_unit='hours', notify_interval=1),
    ]

    session.bulk_save_objects(notification_config)

    print('event-reminder: Adding dummy users data to db...')
    users = [
        User(username=f'{admin_username}',
             email=f'{admin_username}@niepodam.pl',
             password_hash=generate_password_hash(f'{admin_passwd}'),
             access_granted=True,
             role_id=1),
        User(username='john_doe',
             email='john_doe@niepodam.pl',
             password_hash=generate_password_hash(f'{user_passwd}'),
             access_granted=True,
             role_id=2),
        User(username='marry',
             email='marry@niepodam.pl',
             password_hash=generate_password_hash(f'{user_passwd}'),
             access_granted=True,
             role_id=2),
        User(username='test_user',
             email='test_user@niepodam.pl',
             password_hash=generate_password_hash(f'{user_passwd}'),
             access_granted=True,
             role_id=2),
        User(username='harry',
             email='harry@niepodam.pl',
             password_hash=generate_password_hash(f'{user_passwd}'),
             access_granted=False,
             role_id=2),
        User(username='ponton',
             email='ponton@niepodam.pl',
             password_hash=generate_password_hash(f'{user_passwd}'),
             access_granted=True,
             role_id=2),
        User(username='shrek',
             email='shrek@niepodam.pl',
             password_hash=generate_password_hash(f'{user_passwd}'),
             access_granted=True,
             role_id=2),
        User(username='john.box',
             email='john.box@niepodam.pl',
             password_hash=generate_password_hash(f'{user_passwd}'),
             access_granted=True,
             role_id=2),
        User(username='tom.mustang',
             email='tom.mustang@niepodam.pl',
             password_hash=generate_password_hash(f'{user_passwd}'),
             access_granted=True,
             role_id=2),
        User(username='john_bravo',
             email='john_brav@niepodam.pl',
             password_hash=generate_password_hash(f'{user_passwd}'),
             access_granted=False,
             role_id=2),
        User(username='luk.brown',
             email='luk.brown@niepodam.pl',
             password_hash=generate_password_hash(f'{user_passwd}'),
             access_granted=False,
             role_id=2),
    ]

    session.bulk_save_objects(users)

    today = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    today_with_minutes = datetime.utcnow().replace(second=0, microsecond=0)

    # Add some dummy data (events)
    print('event-reminder: Adding dummy data events to db...')

    events = [
        Event(title='Visit to the dentist',
              details='Tearing out three teeth. Doctor - John McDonald. Address - 132, Giant bird street',
              time_creation=today - timedelta(days=2, hours=2),
              all_day_event=False,
              time_event_start=today + timedelta(days=2, hours=2),
              time_event_stop=today + timedelta(days=2, hours=4),
              to_notify=True,
              time_notify=today + timedelta(days=1),
              author_uid=random_user_id(),
              ),
        Event(title='Visit to the vet',
             details='Vestibulum condimentum, enim vitae tempor malesuada, sem sem tempor erat, eget aliquam ex '
                     'lectus at erat. Maecenas viverra blandit neque. Donec malesuada sed odio ut convallis.',
             time_creation=today - timedelta(days=3, hours=6),
             all_day_event=False,
             time_event_start=today + timedelta(days=8, hours=1),
             time_event_stop=today + timedelta(days=8, hours=2),
             to_notify=True,
             time_notify=today + timedelta(days=1),
             author_uid=random_user_id(),
             ),
        Event(title='Extension of car insurance',
              details='Aliquam et egestas enim. Nunc at nisl vitae libero sollicitudin luctus. '
                      'Donec eu purus ipsum. Nam bibendum dictum dolor eu varius. Fusce quis purus consequat.',
              time_creation=today - timedelta(days=1, hours=5),
              all_day_event=True,
              time_event_start=today + timedelta(days=10),
              time_event_stop=today + timedelta(days=10, hours=2),
              to_notify=True,
              time_notify=today + timedelta(days=8),
              author_uid=random_user_id(),
              ),
        Event(title='Journey to Sardinia',
              details='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam non elit sed turpis '
                      'pellentesque consectetur eget non nisl. Integer dignissim, orci ornare pretium gravida, '
                      'odio arcu convallis.',
              time_creation=today - timedelta(days=1, hours=2),
              all_day_event=True,
              time_event_start=today + timedelta(days=5, hours=2),
              time_event_stop=today + timedelta(days=8),
              to_notify=True,
              time_notify=today + timedelta(days=3),
              author_uid=random_user_id(),
              ),
        Event(title='Red Hat System Administration I Course',
              details='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam non elit sed turpis '
                      'pellentesque consectetur eget non nisl. Integer dignissim, orci ornare pretium gravida, '
                      'odio arcu convallis.',
              time_creation=today - timedelta(days=10, hours=2),
              all_day_event=True,
              time_event_start=today - timedelta(days=3),
              time_event_stop=today + timedelta(days=8),
              to_notify=False,
              time_notify=None,
              author_uid=random_user_id(),
              notification_sent=True
              ),
        Event(title='Neque porro quisquam',
              details='Quisque facilisis venenatis nulla vulputate dictum. Cras aliquam sem sapien. Nam lobortis, '
                      'erat ut porttitor sodales, sem urna sagittis turpis, quis venenatis nulla eros ac orci.',
              time_creation=today - timedelta(days=15, hours=2),
              all_day_event=True,
              time_event_start=today - timedelta(days=15, hours=2),
              time_event_stop=today - timedelta(days=13),
              to_notify=True,
              time_notify=today - timedelta(days=18),
              author_uid=random_user_id(),
              notification_sent=True
              ),
        Event(title='Changing wheels in the car',
              details='Quisque facilisis venenatis nulla vulputate dictum. Cras aliquam sem sapien. Nam lobortis, '
                      'erat ut porttitor sodales, sem urna sagittis turpis, quis venenatis nulla eros ac orci.',
              time_creation=today - timedelta(days=15, hours=2),
              all_day_event=False,
              time_event_start=today - timedelta(days=4, hours=5),
              time_event_stop=today - timedelta(days=4),
              to_notify=True,
              time_notify=today - timedelta(days=18),
              author_uid=random_user_id(),
              notification_sent=True
              ),
        Event(title='Beer Call!',
              details='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Pellentesque in turpis eu nisl '
                      'placerat eleifend eu sed lacus. In accumsan sapien sit amet eros dignissim, iaculis '
                      'vulputate velit venenatis.',
              time_creation=today - timedelta(days=15, hours=2),
              all_day_event=False,
              time_event_start=today + timedelta(hours=3),
              time_event_stop=today + timedelta(hours=5),
              to_notify=False,
              time_notify=None,
              author_uid=random_user_id(),
              ),
        Event(title='Fridge repair',
              details='Morbi fermentum nisi eget sapien aliquam, sit amet rutrum sem scelerisque. '
                      'Aliquam ultrices pretium nisl quis pharetra. Phasellus ultricies eros a.',
              time_creation=today - timedelta(days=4),
              all_day_event=False,
              time_event_start=today - timedelta(hours=4),
              time_event_stop=today - timedelta(hours=2),
              to_notify=True,
              time_notify=today - timedelta(days=18),
              author_uid=random_user_id(),
              notification_sent=True
              ),
        Event(title='Aliquam venenatis justo ultrices urna pellentesque ullamcorper.',
              details='Sed tristique ligula elit, eu tempor lectus consectetur sit amet. Curabitur tempus justo et '
                      'massa fringilla, ut vestibulum magna ornare. Sed et libero erat. Ut vel mauris '
                      'at lectus molestie consequat.',
              time_creation=today - timedelta(days=15, hours=2),
              all_day_event=False,
              time_event_start=today - timedelta(hours=2),
              time_event_stop=today + timedelta(hours=4),
              to_notify=True,
              time_notify=today - timedelta(days=5),
              author_uid=random_user_id(),
              notification_sent=True
              ),
        Event(title='Japanese encephalitis vaccination',
              details='Duis congue, urna quis ullamcorper mattis, nisl elit blandit sem, ac tempor lorem diam at sem. '
                      'Phasellus purus purus, euismod eget commodo a, semper eu quam. Ut in consequat metus, '
                      'ut mattis leo. ',
              time_creation=today - timedelta(days=3, hours=2),
              all_day_event=False,
              time_event_start=today + timedelta(hours=18),
              time_event_stop=today + timedelta(hours=22),
              to_notify=True,
              time_notify=today - timedelta(days=2),
              author_uid=random_user_id(),
              notification_sent=True
              ),
        Event(title='CCNA R&S Exam',
              details='Aenean commodo quam eget augue blandit aliquam. Cras ex diam, bibendum ac enim sed, '
                      'iaculis sollicitudin sapien. ',
              time_creation=today - timedelta(days=9, hours=2),
              all_day_event=False,
              time_event_start=today - timedelta(days=8, hours=3),
              time_event_stop=today - timedelta(days=8),
              to_notify=False,
              time_notify=None,
              author_uid=random_user_id(),
              notification_sent=True
              ),
        Event(title='CCNA CyberOPS Exam',
              details='Quisque vitae sapien imperdiet, porttitor leo ut, auctor nulla. Pellentesque eget ipsum '
                      'fermentum, pellentesque lacus ut, pharetra ex.',
              time_creation=today - timedelta(days=5, hours=2),
              all_day_event=False,
              time_event_start=today - timedelta(days=1, hours=8),
              time_event_stop=today - timedelta(days=1, hours=4),
              to_notify=True,
              time_notify=today - timedelta(days=7),
              author_uid=random_user_id(),
              notification_sent=True
              ),
        Event(title='Excursion to Wejherowo',
              details='Estibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; '
                      'Sed efficitur nibh sit amet auctor consectetur. Proin tortor arcu, dapibus eu ornare '
                      'sed, eleifend sed ligula.',
              time_creation=today - timedelta(days=1, hours=2),
              all_day_event=False,
              time_event_start=today + timedelta(days=13),
              time_event_stop=today + timedelta(days=14, hours=4),
              to_notify=True,
              time_notify=today + timedelta(days=7),
              author_uid=random_user_id(),
              ),
        Event(title='Netflix Marathon!',
              details='Remember to buy lots of crisps and beer. The Wither is coming!',
              time_creation=today - timedelta(days=1, hours=2),
              all_day_event=False,
              time_event_start=today - timedelta(days=2, hours=-2),
              time_event_stop=today + timedelta(days=1, hours=4),
              to_notify=True,
              time_notify=today - timedelta(days=3,hours=4),
              author_uid=random_user_id(),
              notification_sent=True
              ),
        Event(title='Pay the bill for the accommodation!',
              details='Pellentesque a posuere sapien. Pellentesque nibh metus, posuere vitae sem vitae, '
                      'varius pellentesque felis. Etiam laoreet cursus condimentum.',
              time_creation=today - timedelta(days=1, hours=2),
              all_day_event=True,
              time_event_start=today + timedelta(days=14),
              time_event_stop=today + timedelta(days=14),
              to_notify=True,
              time_notify=today + timedelta(days=12, hours=4),
              author_uid=random_user_id(),
              ),
        Event(title='Sekurak Hacking Party',
              details='Nulla eget libero a nulla malesuada scelerisque sed vel dolor. '
                      'Nulla ut suscipit felis. Etiam euismod pellentesque lorem ac finibus. '
                      'Vestibulum nulla enim, tincidunt id fringilla commodo, malesuada ut tellus.',
              time_creation=today - timedelta(days=1, hours=2),
              all_day_event=False,
              time_event_start=today + timedelta(days=14, hours=-3),
              time_event_stop=today + timedelta(days=16, hours=2),
              to_notify=True,
              time_notify=today - timedelta(days=11, hours=4),
              author_uid=random_user_id(),
              ),
        Event(title='Water grandma\'s flowers',
              details='Maecenas tempor leo dui, id posuere libero maximus at.',
              time_creation=today - timedelta(days=2, hours=2),
              all_day_event=False,
              time_event_start=today + timedelta(hours=3),
              time_event_stop=today + timedelta(hours=5),
              to_notify=True,
              time_notify=today_with_minutes - timedelta(hours=1),
              author_uid=random_user_id(),
              ),
        Event(title='Take the neighbor\'s dog for a walk',
              details='Nulla ut suscipit felis. Etiam euismod pellentesque lorem ac finibus.',
              time_creation=today - timedelta(days=1, hours=2),
              all_day_event=False,
              time_event_start=today + timedelta(hours=14),
              time_event_stop=today + timedelta(hours=15),
              to_notify=True,
              time_notify=today_with_minutes + timedelta(minutes=3),
              author_uid=random_user_id(),
              ),
        Event(title='Purchase materials for home improvement',
              details='Vestibulum nulla enim, tincidunt id fringilla commodo, malesuada ut tellus.',
              time_creation=today - timedelta(hours=2),
              all_day_event=False,
              time_event_start=today + timedelta(days=5),
              time_event_stop=today + timedelta(days=5, hours=2),
              to_notify=True,
              time_notify=today_with_minutes + timedelta(minutes=6),
              author_uid=random_user_id(),
              ),
        Event(title='Home NAS update',
              details='Nam libero metus, luctus quis bibendum lobortis, tristique a mauris. Pellentesque semper leo '
                      'sit amet dolor semper iaculis. Donec tristique massa a tortor tempus finibus.',
              time_creation=today - timedelta(days=23, hours=10),
              all_day_event=False,
              time_event_start=today - timedelta(days=22, hours=10),
              time_event_stop=today - timedelta(days=22, hours=7),
              to_notify=True,
              time_notify=today_with_minutes - timedelta(days=22, hours=16),
              author_uid=random_user_id(),
              notification_sent=True
              ),
        Event(title='Lorem ipsum dolor sit amet',
              details='Cras molestie viverra dui in tincidunt. Vivamus scelerisque nunc in porta vestibulum.',
              time_creation=today - timedelta(days=22, hours=10),
              all_day_event=True,
              time_event_start=today - timedelta(days=21),
              time_event_stop=today - timedelta(days=19),
              to_notify=True,
              time_notify=today_with_minutes - timedelta(days=22, hours=16),
              author_uid=random_user_id(),
              notification_sent=True
              ),
        Event(title='The oil change in the car',
              details='Fusce id dapibus sem, pellentesque ultrices orci. Pellentesque auctor odio sed lectus '
                      'sagittis dapibus. Nam velit neque, accumsan ac dapibus vel, mattis vel ipsum. Mauris malesuada '
                      'luctus velit, non vestibulum leo laoreet id.',
              time_creation=today - timedelta(days=10, hours=10),
              all_day_event=True,
              time_event_start=today - timedelta(days=9),
              time_event_stop=today - timedelta(days=8),
              to_notify=False,
              author_uid=random_user_id(),
              notification_sent=True,
              is_active=False
              ),
        Event(title='Payment for the VPS',
              details='Phasellus luctus tempus tortor, eu laoreet orci facilisis id. Suspendisse potenti. '
                      'Maecenas bibendum nisi et dictum tempor.',
              time_creation=today - timedelta(days=10, hours=10),
              all_day_event=True,
              time_event_start=today + timedelta(days=9),
              time_event_stop=today + timedelta(days=10),
              to_notify=False,
              author_uid=random_user_id(),
              notification_sent=True,
              is_active=False
              ),
        Event(title='BTC halving day',
              details='Maecenas bibendum nisi et dictum tempor.',
              time_creation=today - timedelta(days=10, hours=9),
              all_day_event=True,
              time_event_start=today - timedelta(days=9),
              time_event_stop=today - timedelta(days=8),
              to_notify=False,
              author_uid=random_user_id(),
              notification_sent=True,
              is_active=True
              ),
        Event(title='Dinner at the mother-in-law\'s',
              details='Ut vitae vehicula mi. Proin ac quam ullamcorper, viverra orci vitae, laoreet tortor. '
                      'Vestibulum lobortis, ligula in accumsan aliquet, lorem neque molestie orci, id maximus '
                      'lorem augue nec erat.',
              time_creation=today - timedelta(days=10, hours=9),
              all_day_event=False,
              time_event_start=today + timedelta(days=11, hours=9),
              time_event_stop=today + timedelta(days=12, hours=10),
              to_notify=True,
              time_notify=today_with_minutes + timedelta(days=8, hours=2),
              author_uid=random_user_id(),
              notification_sent=False,
              is_active=True
              ),
        Event(title='Visit of a mother-in-law',
              details='Ut fringilla tortor ac finibus tincidunt. In sollicitudin ultrices leo, at vehicula nisl '
                      'condimentum vitae. Maecenas placerat elit quis nisl fermentum semper. '
                      'Aliquam sit amet massa vel massa consequat vestibulum nec at lorem.',
              time_creation=today - timedelta(days=11, hours=9),
              all_day_event=False,
              time_event_start=today - timedelta(days=7, hours=1),
              time_event_stop=today - timedelta(days=5, hours=2),
              to_notify=False,
              author_uid=random_user_id(),
              notification_sent=True,
              is_active=False,
              ),
        Event(title='Neque porro quisquam',
              details='Aliquam sit amet massa vel massa consequat vestibulum nec at lorem.',
              time_creation=today - timedelta(days=11, hours=9),
              all_day_event=False,
              time_event_start=today - timedelta(days=6, hours=2),
              time_event_stop=today - timedelta(days=4, hours=3),
              to_notify=False,
              author_uid=random_user_id(),
              notification_sent=True,
              is_active=True,
              ),
        Event(title='Ut vitae vehicula mi',
              details='Curabitur aliquet pretium leo sit amet auctor. Donec dapibus, neque eget ullamcorper malesuada, '
                      'purus tellus posuere risus, a rutrum tortor lacus ac turpis.',
              time_creation=today - timedelta(days=15, hours=2),
              all_day_event=False,
              time_event_start=today - timedelta(days=13, hours=4),
              time_event_stop=today - timedelta(days=11, hours=1),
              to_notify=False,
              author_uid=random_user_id(),
              notification_sent=True,
              is_active=True,
              ),
        Event(title='Repairing garden furniture',
              details='Purus tellus posuere risus, a rutrum tortor lacus ac turpis.',
              time_creation=today - timedelta(days=10, hours=9),
              all_day_event=False,
              time_event_start=today - timedelta(days=7, hours=3),
              time_event_stop=today - timedelta(days=6, hours=12),
              to_notify=False,
              author_uid=random_user_id(),
              notification_sent=True,
              is_active=True,
              ),
        Event(title='Visit of the plumber',
              details='Purus tellus posuere risus, a rutrum tortor lacus ac turpis.',
              time_creation=today - timedelta(days=10, hours=3),
              all_day_event=False,
              time_event_start=today - timedelta(days=7, hours=0),
              time_event_stop=today - timedelta(days=6, hours=20),
              to_notify=False,
              author_uid=random_user_id(),
              notification_sent=True,
              is_active=True,
              ),
        Event(title='Business trip to Warsaw',
              details='Vestibulum lobortis, ligula in accumsan aliquet, lorem neque molestie orci, '
                      'id maximus lorem augue nec erat.',
              time_creation=today - timedelta(days=1, hours=3),
              all_day_event=True,
              time_event_start=today + timedelta(days=9),
              time_event_stop=today + timedelta(days=11),
              to_notify=True,
              time_notify=today_with_minutes + timedelta(days=7, hours=2),
              author_uid=random_user_id(),
              notification_sent=True,
              is_active=True,
              ),
        Event(title='Business trip to Zakopane',
              details='Ut hendrerit et lectus in dignissim. Quisque tristique odio leo, ut maximus justo dapibus ac. '
                      'Pellentesque euismod velit arcu, sed venenatis ipsum tincidunt ac. Aliquam non gravida lorem.',
              time_creation=today - timedelta(days=10, hours=3),
              all_day_event=True,
              time_event_start=today + timedelta(days=12),
              time_event_stop=today + timedelta(days=14),
              to_notify=True,
              time_notify=today_with_minutes + timedelta(days=10, hours=6),
              author_uid=random_user_id(),
              notification_sent=True,
              is_active=True,
              ),
        Event(title='Business trip to Poznan',
              details='Proin quis metus vel nunc fermentum viverra. Maecenas a lacus dapibus, consectetur quam et, '
                      'auctor dui.',
              time_creation=today - timedelta(days=14, hours=6),
              all_day_event=True,
              time_event_start=today - timedelta(days=12, hours=5),
              time_event_stop=today - timedelta(days=11, hours=3),
              to_notify=False,
              author_uid=random_user_id(),
              notification_sent=False,
              is_active=True,
              ),
        Event(title='Test event',
              details=' Maecenas a lacus dapibus, consectetur quam et, auctor dui.',
              time_creation=today - timedelta(days=25, hours=6),
              all_day_event=True,
              time_event_start=today - timedelta(days=6, hours=5),
              time_event_stop=today - timedelta(days=4, hours=3),
              to_notify=False,
              author_uid=random_user_id(),
              notification_sent=False,
              is_active=True,
              ),
    ]

    session.bulk_save_objects(events)

    # Fetch users with user role
    users_ids = session.query(User).filter(User.role_id != 1).all()

    # Assign the event to a user (users) who should be notified (choose by random).
    for event in session.query(Event).filter(Event.to_notify == True).all():
        # No more than 3 users to to be notified.
        for user in random.sample(users_ids, k=random.randint(1, 3)):
            event.notified_users.append(user)

    session.commit()

    print(f'event-reminder: New SQLite db - {db_name} has been created!!!')
