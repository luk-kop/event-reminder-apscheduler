from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from reminder import db
from reminder.models import Role, User
from reminder.forms import LoginForm
from werkzeug.urls import url_parse
from logging.handlers import RotatingFileHandler
import logging


auth_bp = Blueprint('auth_bp', __name__,
                    template_folder='templates',
                    static_folder='static')


@auth_bp.before_request
def update_last_seen():
    """
    Update when the current user was last seen (User.last_seen attribute).
    """
    if request.method == "POST":    # only for tests
        print(request.form)
    if current_user.is_authenticated:
        current_user.user_seen()
        db.session.commit()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Check whether user is logged in
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.index'))
    form = LoginForm()
    if form.validate_on_submit():
        current_app.logger_auth.debug(f'Login attempt: {request.remote_addr}, '
                                      f'{request.user_agent.platform}, {request.user_agent.browser} {request.user_agent.version}')
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.access_granted or not user.check_password(form.password.data):
            flash('Login Unsuccessful. Please check username and password', 'danger')
            current_app.logger_auth.warning(f'Failed to log in. Username data entered: "{form.username.data}"')
            if user and user.access_granted:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 3:
                    user.access_granted = False
                    current_app.logger_auth.warning(f'User "{user.username}" account has been blocked')
                db.session.commit()
            return redirect(url_for('auth_bp.login'))
        # below function will register the user as logged in
        login_user(user, remember=form.remember_me.data)
        current_app.logger_auth.info(f'"{user.username}" has been successfully authenticated')
        # reset login attempts
        user.failed_login_attempts = 0
        db.session.commit()
        # next page value obtained from query string
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main_bp.index')
        flash('You have been successfully logged in!', 'success')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@auth_bp.route('/logout')
def logout():
    """
    Logout user and redirect to 'home'
    """
    current_app.logger_auth.info(f'"{current_user.username}" has been successfully logged off')
    logout_user()
    flash('You have been successfully logged out!', 'success')
    return redirect(url_for('main_bp.index'))