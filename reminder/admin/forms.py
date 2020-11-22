from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField
from wtforms.validators import InputRequired, EqualTo, Regexp, Length, NumberRange, Optional, Email

from reminder.custom_wtforms import MxRecordValidator


class NewUserForm(FlaskForm):
    """
    Validators for a new user account.
    """
    username = StringField(validators=[InputRequired(),
                                       Length(min=3, max=40),
                                       Regexp(regex='^[a-zA-Z0-9][a-zA-Z0-9\._-]{1,39}[a-zA-Z0-9]$',
                                              message='Username should contain chars (min 3): a-z, A-Z, 0-9, . _ -')])
    email = StringField(validators=[InputRequired(),
                                    Email(message='Please enter valid email address'),
                                    Length(max=70),
                                    MxRecordValidator()])
    role = SelectField(choices=[('user', 'User'), ('admin', 'Admin')])
    access = SelectField(label='Can log in?',
                         choices=[('False', 'No'), ('True', 'Yes')])
    pass_reset = SelectField(label='Change password on next login?',
                             choices=[('False', 'No'), ('True', 'Yes')])
    password = PasswordField(validators=[Regexp(regex='^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]'
                                                      '{8,40}$',
                                                message='Password must contain minimum 8 characters, at least one '
                                                        'letter, one number and one special character')])
    password2 = PasswordField(label='Confirm password',
                              validators=[EqualTo('password')])


class EditUserForm(NewUserForm):
    """
    Validators for the user being edited
    """
    # the password field can be blank (empty) or match the regex pattern
    password = PasswordField(label='Password',
                             validators=[Regexp(regex='^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]'
                                                      '{8,40}$|^$',
                                                message='Password must contain minimum 8 characters, at least one '
                                                        'letter, one number and one special character')])
    password2 = PasswordField(label='Confirm password', validators=[EqualTo('password')])


class NotifyForm(FlaskForm):
    """
    Validators for notification settings
    """
    notify_status = StringField(label='Notification status',
                                validators=[Regexp(regex='^on$'), Optional()])
    notify_unit = SelectField('Notification interval time units',
                              choices=[('hours', 'hours'), ('minutes', 'minutes'), ('seconds', 'seconds')])
    notify_interval = IntegerField(label='Notification interval',
                                   validators=[InputRequired(), NumberRange(min=1)])
    mail_server = StringField(label='Mail server',
                              validators=[InputRequired(),
                                          Length(max=70)])
    mail_port = IntegerField(label='Mail port',
                             validators=[InputRequired(), NumberRange(min=1)])
    mail_security = SelectField(label='Mail security',
                                choices=[('tls', 'TLS'), ('ssl', 'SSL')])
    mail_username = StringField(label='Mail username',
                                validators=[InputRequired(),
                                            Length(max=70)])