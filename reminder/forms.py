from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField, BooleanField, PasswordField, DateField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from reminder.models import User, Role


class EventForm(FlaskForm):
    pass
    choices = []
    for user in User.query.all():
        choices.append((user.id, user.username))

    title = StringField('Title', validators=[DataRequired(), Length(min=1, max=50)])
    details = TextAreaField('Event description:', validators=[Length(min=0, max=200)])
    time_event = DateField('Event Date', format='%d.%m.%Y', validators=[DataRequired()])
    to_notify = BooleanField('Notify?', default="checked")
    time_notify = DateField('Reminder Date', format='%d.%m.%Y', validators=[DataRequired()])
    notified_user = SelectMultipleField('User to notify', choices=choices, validators=[DataRequired()])
    submit = SubmitField('Submit')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class NewUserForm(FlaskForm):
    choices = [
        (f'{Role.query.filter_by(name="admin").first().id}', 'Admin'),
        (f'{Role.query.filter_by(name="user").first().id}', 'User')
    ]

    username = StringField('Username', validators=[DataRequired()])
    # below Email() validator ensure that what the user types in this field matches the structure of an email address
    email = StringField('Email', validators=[DataRequired(), Email()])
    # can_login = BooleanField('User can login?')
    # is_admin = BooleanField('Is the user admin?')
    # Role.query.filter_by(name='admin').first().id
    role = SelectField('Role', choices=choices, validators=[DataRequired()])
    password = PasswordField('Password')
    password2 = PasswordField('Repeat Password', [EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Add User')

    # When you add any methods that match the pattern 'validate_<field_name>',
    # WTForms takes those as custom validators and invokes them in addition to the stock validators
    def validate_username(self, username):
        """Check wheather user with this username already exist in db"""
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('That username is taken. Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('That emial  is taken. Please use a different email address.')