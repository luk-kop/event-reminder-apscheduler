import logging
from datetime import datetime

from reminder.models import Log


class DatabaseHandler(logging.Handler):
    """
    Custom log handler that emits logs to the db.
    """
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s'))
        self.setLevel(logging.DEBUG)

    def emit(self, record):

        self.format(record)

        log_time = datetime.strptime(record.__dict__['asctime'], "%Y-%m-%d %H:%M:%S,%f")

        log_record = Log(time=log_time,
                         log_name=record.__dict__['name'],
                         level=record.__dict__['levelname'],
                         msg=record.__dict__['message'])

        self.session.add(log_record)
        self.session.commit()