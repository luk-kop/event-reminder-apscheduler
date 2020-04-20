from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from reminder import db, scheduler
from reminder.models import Role, User, Event
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from functools import wraps
from sqlalchemy import func, or_
import datetime
from reminder.main import main


admin_bp = Blueprint('admin_bp', __name__,
                     template_folder='templates',
                     static_folder='static')


def admin_required(func):
    """
    Decorator check if current user has admin privileges.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)
        return func(*args, **kwargs)
    return wrapper


def background_job():
    """
    Run process in background.
    """
    print('test')


@admin_bp.before_request
def update_last_seen():
    """
    Update when the current user was last seen (User.last_seen attribute).
    """
    #print(scheduler.running)
    if request.method == "POST":    # only for tests
        print(request.form)
    if current_user.is_authenticated:
        current_user.user_seen()
        db.session.commit()


@admin_bp.route('/events')
@login_required
@admin_required
def events():
    """
    Display all events from db in Admin Portal.
    """
    # print(request.referrer) # print previous URL
    events = Event.query.order_by("time_event_start").all()
    return render_template('admin/events.html', events=events, title='Events')


@admin_bp.route('/event/<int:event_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def event(event_id):
    """
    Display particular event's details.
    The event details in Admin Portal.
    """
    event = Event.query.filter_by(id=event_id).first_or_404()
    # Fetch users that can be notified (only with user role)
    users_to_notify = User.query.filter_by(role_id=2).all()
    today = datetime.date.today().strftime("%Y-%m-%d")

    if request.method == "POST":
        # If a "Cancel" button has been pressed.
        if request.form.get('cancel-btn') == 'Cancel':
            return redirect(url_for('admin_bp.events'))

        event.title = request.form.get('title')
        event.details = request.form.get('details')
        event.all_day_event = True if request.form.get('allday') == 'True' else False
        event.to_notify = True if request.form.get('to_notify') == 'True' else False
        event.time_notify = main.str_to_datetime(request.form.get('date_notify')) if request.form.get(
            'date_notify') else None
        event.notification_sent = True if request.form.get('notify_sent') == 'True' else False

        # Check if all day event or not.
        if request.form.get('time_event_start'):
            time_event_start_db = main.str_to_datetime(request.form.get('date_event_start'),
                                                  request.form.get('time_event_start'))
            time_event_stop_db = main.str_to_datetime(request.form.get('date_event_stop'),
                                                 request.form.get('time_event_stop'))
        else:
            time_event_start_db = main.str_to_datetime(request.form.get('date_event_start'))
            time_event_stop_db = main.str_to_datetime(request.form.get('date_event_stop'))
        event.time_event_start = time_event_start_db
        event.time_event_stop = time_event_stop_db

        # Set users to notify. If "to_notify = False" the list "user_form" is []
        users_form = request.form.getlist('notified_user')
        # Overwrite current users to notify.
        event.notified_uids = [User.query.get(user_id) for user_id in users_form]
        db.session.commit()
        flash('Your changes have been saved!', 'success')
        return redirect(url_for('admin_bp.events'))
    return render_template('admin/event.html', event=event, title='Event details', users=users_to_notify, today=today)




@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """
    List user's data from db in Admin Portal.
    """
    users = User.query.order_by(func.lower(User.username).asc()).all()
    return render_template('admin/users.html', users=users, title='Users')


def check_user_exist(request, user_edited=None):
    """
    Check if username and email already exist in db.

    """
    username_from_form = request.form.get('username')
    email_from_form = request.form.get('email')
    user_exist, email_exist = None, None

    if user_edited:
        # When the user is edited
        if user_edited.username != username_from_form:
            user_exist = User.query.filter_by(username=username_from_form).first()
        if user_edited.email != email_from_form:
            email_exist = User.query.filter_by(email=email_from_form).first()
    else:
        # When a new user is created
        user_exist = User.query.filter_by(username=username_from_form).first()
        email_exist = User.query.filter_by(email=email_from_form).first()
    if user_exist or email_exist:
        access_from_form = True if request.form.get('access') == 'True' else False
        roleid_from_form = request.form.get('role')
        form_content = {
            'username': username_from_form,
            'email': email_from_form,
            'access': access_from_form,
            'roleid': True if roleid_from_form == 'admin' else False
        }
        if user_exist and email_exist:
            flash(f'Sorry! Username "{username_from_form}" and email "{email_from_form}" are already taken. '
                  f'Please try something different.', 'danger')
        elif email_exist:
            flash(f'Sorry! Email "{email_from_form}" is already taken. Please try something different.', 'danger')
        else:
            flash(f'Sorry! Username "{username_from_form}" is already taken. Please try something different.', 'danger')
        return form_content


@admin_bp.route('/new_user', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    """
    Add new user to db.
    """
    if request.method == "POST":
        # If a "Cancel" button has been pressed.
        if request.form.get('cancel-btn') == 'Cancel':
            return redirect(url_for('admin_bp.users'))
        # Check if username and email already exist in db.
        form_content = check_user_exist(request)
        if form_content:
            return render_template('admin/new_user.html', title='New user', form_content=form_content)
        user = User(username=request.form.get('username'),
                    email=request.form.get('email'),
                    access_granted=True if request.form.get('access') == 'True' else False,
                    role_id=str(Role.query.filter_by(name=request.form.get('role')).first().id))
        if request.form.get('password'):
            user.set_password(request.form.get('password'))
        else:
            user.set_password(app.config['USER_DEFAULT_PASS'])
        db.session.add(user)
        db.session.commit()
        flash(f'User "{user.username}" has been added!', 'success')
        return redirect(url_for('admin_bp.users'))
    return render_template('admin/new_user.html', title='New user')


@admin_bp.route('/user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def user(user_id):
    """
    Editing an user already existing in the db.
    """
    user = User.query.filter_by(id=user_id).first_or_404()
    if request.method == "POST":
        # If a "Cancel" button has been pressed.
        if request.form.get('cancel-btn') == 'Cancel':
            return redirect(url_for('admin_bp.users'))
        # Check if new assigned username or email exist in db.
        form_content = check_user_exist(request, user)
        if form_content:
            return render_template('admin/user.html', user=user)

        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.access_granted = True if request.form.get('access') == 'True' else False
        user.role_id = str(Role.query.filter_by(name=request.form.get('role')).first().id)
        # check if password has been changed
        # if request.form.password and not user.check_password(request.form.password):
        #     user.set_password(request.form.password)
        db.session.commit()
        flash('Your changes have been saved!', 'success')
        return redirect(url_for('admin_bp.users'))
    return render_template('admin/user.html', user=user)


@admin_bp.route('/del_user/<int:user_id>')
@login_required
@admin_required
def del_user(user_id):
    """
    Delete user data in db.
    """
    if current_user.id == user_id:
        flash("Sorry! You can't delete yourself!", 'danger')
        return redirect(url_for('admin_bp.users'))
    user = User.query.filter_by(id=user_id).first()
    db.session.delete(user)
    db.session.commit()
    flash(f'User "{user.username}" has been deleted!', 'success')
    return redirect(url_for('admin_bp.users'))


@admin_bp.route('/del_event/<int:event_id>')
@login_required
@admin_required
def del_event(event_id):
    """
    Delete event data from db - permanent.
    """
    event = Event.query.filter_by(id=event_id).first()
    db.session.delete(event)
    db.session.commit()
    flash(f'Event with title "{event.title}" has been permanently deleted!', 'success')
    return redirect(url_for('admin_bp.events'))


@admin_bp.route('/act_event/<int:event_id>')
@login_required
@admin_required
def act_event(event_id):
    """
    Activate the event to make it visible to standard users.
    """
    event = Event.query.filter_by(id=event_id).first()
    if event.is_active:
        event.is_active = False
        db.session.commit()
        flash(f'Event with title "{event.title}" has been deactivated!', 'success')
    else:
        event.is_active = True
        db.session.commit()
        flash(f'Event with title "{event.title}" has been activated!', 'success')
    return redirect(url_for('admin_bp.events'))


@admin_bp.route('/notify/')
@login_required
@admin_required
def notify():
    test = ''
    if test == 'start':
        scheduler.print_jobs()
        # check weather some scheduler jobs exist
        if not scheduler.get_jobs():
            print('brak jobs!!!')
        scheduler.add_job(background_job, trigger='interval', seconds=3, replace_existing=True, max_instances=1, id='my_job_id')
        if scheduler.running:
            print('is running')
        flash('The notify service is running!', 'success')
    elif test == 1:
        print('test test')
        scheduler.print_jobs()
        print(scheduler.get_jobs())
        if scheduler.get_jobs():
            print('jest job')
        scheduler.remove_job('my_job_id')
        # scheduler.shutdown(wait=True)
        if not scheduler.running:
            print('NOT running')
        flash('The notify service has been turned off!', 'success')
    return render_template('admin/notify.html')


@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    """
    List logs.
    """
    return 'logs test'