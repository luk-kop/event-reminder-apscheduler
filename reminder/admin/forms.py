from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import InputRequired, EqualTo, Regexp, Length
from wtforms.fields.html5 import EmailField


class NewUserForm(FlaskForm):
    """
    Validators for a new user account.
    """
    username = StringField(label='Username',
                           validators=[InputRequired(),
                                       Length(min=3, max=40),
                                       Regexp(regex='^[a-zA-Z0-9][a-zA-Z0-9\._-]{1,39}[a-zA-Z0-9]$',
                                              message='Username should contain chars (min 3): a-z, A-Z, 0-9, . _ -')])
    email = EmailField(label='Email',
                       validators=[InputRequired(message='Please enter valid email address'),
                                   Length(max=70)])
    role = SelectField('Role',
                       choices=[('user', 'User'), ('admin', 'Admin')])
    access = SelectField('Can log in?',
                         choices=[('False', 'No'), ('True', 'Yes')])
    pass_reset = SelectField('Change password on next login?',
                             choices=[('False', 'No'), ('True', 'Yes')])
    password = PasswordField(label='Password',
                             validators=[Regexp(regex='^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]'
                                                      '{8,40}$',
                                                message='Password must contain minimum 8 characters, at least one '
                                                        'letter, one number and one special character')])
    password2 = PasswordField(label='Confirm password', validators=[EqualTo('password')])


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