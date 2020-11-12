from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TimeField, SelectMultipleField
from wtforms.validators import InputRequired, Length

from reminder.custom_wtforms import DateOrTimeChecker


class NewEventForm(FlaskForm):
    """
    Validators for a newly added event.
    """
    title = StringField(label='Title',
                        validators=[InputRequired(),
                                    Length(max=80)])
    details = StringField(label='Details',
                        validators=[Length(max=300)])
    allday = SelectField('All day event?',
                         choices=[('True', 'Yes'), ('False', 'No')])
    date_event_start = DateField(label='Event start',
                                 validators=[InputRequired()])
    time_event_start = TimeField(label='Event start time')
    date_event_stop = DateField(label='Event stop',
                                validators=[InputRequired(),
                                            DateOrTimeChecker(other_field='date_event_start',
                                                              later_than=True)])
    time_event_stop = TimeField(label='Event stop time',
                                validators=[DateOrTimeChecker(other_field='time_event_start',
                                                              later_than=True,
                                                              time_check=True)])
    to_notify = SelectField(label='Notify?',
                            choices=[('True', 'Yes'), ('False', 'No')])
    date_notify = DateField(label='Reminder date',
                            validators=[DateOrTimeChecker(other_field='date_event_start',
                                                          earlier_than=True)])
    time_notify = TimeField(label='Reminder time')
    notified_user = SelectMultipleField(label='Users to notify')