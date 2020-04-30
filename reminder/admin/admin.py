from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from reminder import db, scheduler
from reminder.models import Role, User, Event, Notification
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from functools import wraps
from sqlalchemy import func, or_, desc, asc
import datetime
from reminder.main import main
from reminder.admin import smtp_mail
import logging
from logging.handlers import RotatingFileHandler


admin_bp = Blueprint('admin_bp', __name__,
                     template_folder='templates',
                     static_folder='static')

# logger for the admin blueprint
logs_dir = current_app.config['LOGS_DIR']
logger_admin = logging.getLogger("admin.auth")
file_handler_admin = RotatingFileHandler(f'{logs_dir}/admin.log', maxBytes=30720, backupCount=5)
file_handler_admin.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S'))
logger_admin.setLevel(logging.DEBUG)
logger_admin.addHandler(file_handler_admin)


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
    # get the app object
    app = scheduler.app
    with app.app_context():
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        print(today)    # only for tests
        events_to_notify = Event.query.filter(Event.time_notify <= today,
                                              Event.is_active == True,
                                              Event.to_notify == True,
                                              Event.notification_sent == False).all()
        try:
            for event in events_to_notify:
                users_to_notify = [user for user in event.notified_uids]
                print(f'{event}, {event.time_notify}, {event.notification_sent} {users_to_notify}', )
                smtp_mail.send_email('Attention! Upcoming event!',
                           users_to_notify,
                           event)
                logger_admin.info(f'Notification service. Mail sent to: {users_to_notify}')
                print(f'Mail sent to {users_to_notify}')
                event.notification_sent = True
                db.session.commit()
        except Exception as error:
            logger_admin.error(f'Background job error: {error}')
            # Remove job when error occure.
            scheduler.remove_job('my_job_id')


@admin_bp.before_request
def update_last_seen():
    """
    Update when the current user was last seen (User.last_seen attribute).
    """
    #print(scheduler.running)
    if request.method == "POST":    # only for tests
        print(f'\n{request.form}\n')
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
    if not request.args or (request.args.get('col') == 'start' and request.args.get('dir') == 'asc'):
        events = Event.query.order_by("time_event_start").all()
    elif request.args.get('col') == 'id' and request.args.get('dir') == 'desc':
        events = Event.query.order_by(desc(Event.id)).all()
    elif request.args.get('col') == 'id' and request.args.get('dir') == 'asc':
        events = Event.query.order_by(asc(Event.id)).all()
    elif request.args.get('col') == 'start' and request.args.get('dir') == 'desc':
        events = Event.query.order_by(desc(Event.time_event_start)).all()
    elif request.args.get('col') == 'id' and request.args.get('dir') == 'asc':
        events = Event.query.order_by(asc(Event.time_event_start)).all()
    elif request.args.get('col') == 'stop' and request.args.get('dir') == 'desc':
        events = Event.query.order_by(desc(Event.time_event_stop)).all()
    elif request.args.get('col') == 'stop' and request.args.get('dir') == 'asc':
        events = Event.query.order_by(asc(Event.time_event_stop)).all()
    elif request.args.get('col') == 'title' and request.args.get('dir') == 'asc':
        events = Event.query.order_by(func.lower(Event.title).asc()).all()
    elif request.args.get('col') == 'title' and request.args.get('dir') == 'desc':
        events = Event.query.order_by(func.lower(Event.title).desc()).all()
    elif request.args.get('col') == 'notify' and request.args.get('dir') == 'yes':
        events = Event.query.filter(Event.to_notify == True).all() + Event.query.filter(Event.to_notify == False).all()
    elif request.args.get('col') == 'notify' and request.args.get('dir') == 'no':
        events = Event.query.filter(Event.to_notify == False).all() + Event.query.filter(Event.to_notify == True).all()
    elif request.args.get('col') == 'active' and request.args.get('dir') == 'no':
        events = Event.query.filter(Event.is_active == False).all() + Event.query.filter(Event.is_active == True).all()
    elif request.args.get('col') == 'active' and request.args.get('dir') == 'yes':
        events = Event.query.filter(Event.is_active == True).all() + Event.query.filter(Event.is_active == False).all()
    else:
        abort(404)
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
        if request.form.get('date_notify'):
            event.time_notify = main.str_to_datetime(request.form.get('date_notify'),
                                                     request.form.get('time_notify'))
        else:
            event.time_notify = None
        event.notification_sent = True if request.form.get('notify_sent') == 'True' else False

        # Check if event ia all_day event or not.
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
            user.set_password(current_app.config['USER_DEFAULT_PASS'])
        db.session.add(user)
        db.session.commit()
        logger_admin.info(f'User "{user.username}" has been added to db')
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
        if request.form.get('access') == 'True' and str(user.access_granted) != request.form.get('access'):
            user.failed_login_attempts = 0
        user.access_granted = True if request.form.get('access') == 'True' else False
        user.role_id = str(Role.query.filter_by(name=request.form.get('role')).first().id)
        # check if password has been changed
        # if request.form.password and not user.check_password(request.form.password):
        #     user.set_password(request.form.password)
        db.session.commit()
        logger_admin.info(f'User "{user.username}" data has been changed')
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
    logger_admin.warning(f'User "{user.username} has been deleted from db"')
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


@admin_bp.route('/notify/', methods=['GET', 'POST'])
@login_required
@admin_required
def notify():
    """
    Func allows to start notification service and change the service configuration.
    """
    # Notification config data (for interval and interval unit).
    notification_config = Notification.query.first()
    # Mail config data.
    notify_config = {
        'mail_server': current_app.config['MAIL_SERVER'],
        'mail_port': current_app.config['MAIL_PORT'],
        'mail_security': current_app.config['MAIL_SECURITY'],
        'mail_username': current_app.config['MAIL_USERNAME'],
        'notify_unit': notification_config.notify_unit,
        'notify_interval': notification_config.notify_interval,
    }

    if request.method == "POST":
        # If a "Cancel" button has been pressed.
        if request.form.get('cancel-btn') == 'Cancel':
            return redirect(url_for('admin_bp.users'))

        # Fetch data from form.
        notify_status_form = request.form.get('notify_status')
        notify_unit_form = request.form.get('notify_unit')
        notify_interval_form = request.form.get('notify_interval')
        mail_server_form = request.form.get('mail_server')
        mail_port_form = request.form.get('mail_port')
        mail_security_form = request.form.get('mail_security')
        mail_username_form = request.form.get('mail_username')
        mail_password_form = request.form.get('mail_password')

        # Update the data in 'notify_config' div and config object (if required).
        if mail_server_form != notify_config['mail_server']:
            current_app.config['MAIL_SERVER'] = mail_server_form
            notify_config['mail_server'] = mail_server_form
        if mail_port_form != notify_config['mail_port']:
            current_app.config['MAIL_PORT'] = mail_port_form
            notify_config['mail_port'] = mail_port_form
        if mail_security_form != notify_config['mail_security']:
            current_app.config['MAIL_SECURITY'] = mail_security_form
            notify_config['mail_security'] = mail_security_form
        if mail_username_form != notify_config['mail_username']:
            current_app.config['MAIL_USERNAME'] = mail_username_form
            notify_config['mail_username'] = mail_username_form
        if mail_password_form:
            current_app.config['MAIL_PASSWORD'] = mail_password_form

        # check weather some scheduler jobs exist
        # if scheduler.running:
        # print(scheduler.get_jobs())

        # Test mail configuration before running service
        if notify_status_form == 'on':
            test_mail_config = smtp_mail.test_email()
        else:
            test_mail_config = False

        # Test mail configuration before running service.
        if not notify_status_form and scheduler.get_jobs():
            scheduler.remove_job('my_job_id')
            logger_admin.info(f'Notification service has been turned off by "{current_user.username}"')
            flash('The notify service has been turned off!', 'success')
        elif scheduler.get_jobs() and not test_mail_config:
            scheduler.remove_job('my_job_id')
        elif notify_status_form == 'on' and test_mail_config:
            if not scheduler.get_jobs():
                logger_admin.info(f'Notification service has been started by "{current_user.username}"')
            else:
                logger_admin.info(f'Notification service config has been changed by "{current_user.username}"')
            if notify_unit_form == 'seconds':
                scheduler.add_job(func=background_job, trigger='interval', replace_existing=True, max_instances=1,
                                  seconds=int(notify_interval_form), id='my_job_id')
            elif notify_unit_form == 'minutes':
                scheduler.add_job(func=background_job, trigger='interval', replace_existing=True, max_instances=1,
                                  minutes=int(notify_interval_form), id='my_job_id')
            else:
                scheduler.add_job(func=background_job, trigger='interval', replace_existing=True, max_instances=1,
                                  hours=int(notify_interval_form), id='my_job_id')
            flash('Connection with mail server established correctly! The notify service is running!', 'success')

        # Save notification settings to db.
        if notify_unit_form != notify_config['notify_unit'] or notify_interval_form != notify_config['notify_interval']:
            notification_config.notify_unit = notify_unit_form
            notification_config.notify_interval = int(notify_interval_form)
            db.session.commit()
            if not scheduler.get_jobs():
                logger_admin.info(f'Notification service config has been changed by "{current_user.username}"')

        # Update the rest of the data in 'notify_config' dic.
        notify_config['notify_unit'] = notify_unit_form
        notify_config['notify_interval'] = notify_interval_form

    service_run = True if scheduler.get_jobs() else False
    return render_template('admin/notify.html', service_run=service_run, **notify_config)


@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    """
    List logs.
    """
    pass
    return render_template('admin/logs.html')