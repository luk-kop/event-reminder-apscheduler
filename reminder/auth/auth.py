from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from reminder import db
from reminder.models import Role, User
from reminder.forms import EventForm, LoginForm, NewUserForm
from werkzeug.urls import url_parse
from werkzeug.exceptions import HTTPException


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
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.access_granted or not user.check_password(form.password.data):
            flash('Login Unsuccessful. Please check username and password', 'danger')
            return redirect(url_for('auth_bp.login'))
        # below function will register the user as logged in
        login_user(user, remember=form.remember_me.data)
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
    logout_user()
    flash('You have been successfully logged out!', 'success')
    return redirect(url_for('main_bp.index'))