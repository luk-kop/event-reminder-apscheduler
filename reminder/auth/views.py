from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, session
from flask_login import current_user, login_user, logout_user
from werkzeug.urls import url_parse

from reminder.extensions import db
from reminder.models import User
from reminder.auth.forms import LoginForm
from reminder.custom_decorators import login_required, cancel_click


auth_bp = Blueprint('auth_bp', __name__,
                    template_folder='templates',
                    static_folder='static')


@auth_bp.before_request
def update_last_seen():
    """
    Update when the current user was last seen (User.last_seen attribute).
    """
    if current_user.is_authenticated:
        current_user.user_seen()
        db.session.commit()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Log in user.
    """
    # Check whether user is logged in
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.index'))
    form = LoginForm()
    if form.validate_on_submit():
        current_app.logger_auth.debug(f'Login attempt: {request.remote_addr}, '
                                      f'{request.user_agent.platform}, {request.user_agent.browser} '
                                      f'{request.user_agent.version}')
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.access_granted or not user.check_password(form.password.data):
            flash('Login Unsuccessful. Please check username and password!', 'danger')
            current_app.logger_auth.warning(f'Failed to log in. Username data entered: "{form.username.data}"')
            if user and user.access_granted:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 3:
                    user.access_granted = False
                    current_app.logger_auth.warning(f'User "{user.username}" account has been blocked')
                db.session.commit()
            return redirect(url_for('auth_bp.login'))
        # Below function will register the user as logged in
        login_user(user, remember=form.remember_me.data)
        current_app.logger_auth.info(f'"{user.username}" has been successfully authenticated')
        session.permanent = True
        # Reset login attempts
        user.failed_login_attempts = 0
        db.session.commit()
        if current_user.pass_change_req:
            flash('Please change your password', 'success')
            return redirect(url_for('auth_bp.change_pass'))
        # Next page value obtained from query string
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


@auth_bp.route('/change_pass', methods=['GET', 'POST'])
@cancel_click('main_bp.index')
@login_required
def change_pass():
    """
    Change user password.
    """
    if request.method == "POST":
        curr_pass = request.form.get('curr_pass')
        new_pass = request.form.get('password')
        if current_user.check_password(curr_pass):
            # New pass should be different than current one.
            if current_user.check_password(new_pass):
                flash('The new password should be different from the current one!', 'danger')
                return redirect(url_for('auth_bp.change_pass'))
            current_user.set_password(new_pass)
            if current_user.pass_change_req:
                current_user.pass_change_req = False
            db.session.commit()
            current_app.logger_auth.info(f'User "{current_user.username}" changed the password')
            flash('Password has been successfully changed!', 'success')
            return redirect(url_for('main_bp.index'))
        else:
            current_app.logger_auth.warning(f'Failed password change by "{current_user.username}"')
            current_user.failed_login_attempts += 1
            if current_user.failed_login_attempts >= 3:
                current_user.access_granted = False
                current_app.logger_auth.warning(f'User "{current_user.username}" account has been blocked')
                logout_user()
                flash('Password change has been unsuccessful. Your account has been blocked!', 'danger')
                return redirect(url_for('main_bp.index'))
            db.session.commit()
            current_app.logger_auth.warning(f'Failed password change. Current password does not much for '
                                            f'"{current_user.username}"')
            flash('The current password does not match! Please check your password', 'danger')
    return render_template('pass_change.html', title='Change Password')