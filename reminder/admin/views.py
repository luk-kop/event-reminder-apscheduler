import datetime
import json
import time

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app, session
from flask_login import current_user
from sqlalchemy import func, desc, asc
import requests
import elasticsearch.exceptions

from reminder.extensions import db, scheduler, cache
from reminder.models import Role, User, Event, Notification, Log
from reminder.main import views as main_views
from reminder.admin import smtp_mail
from reminder.custom_decorators import admin_required, login_required, cancel_click
from reminder.admin.forms import NewUserForm, EditUserForm, NotifyForm
from reminder.custom_wtforms import flash_errors


admin_bp = Blueprint('admin_bp', __name__,
                     template_folder='templates',
                     static_folder='static')


@admin_bp.before_app_first_request
def before_app_req():
    """
    Refresh an index inside elasticsearch with all the data from the relational side and cash mail config.
    """
    # Add all the events and logs from the db to the search index.
    Event.reindex()
    Log.reindex()
    # Caching mail server config - in order to allow the admin to change the configuration
    # while the application is running (store mail config data in db is not desired)
    cache.set_many({'mail_server': current_app.config.get('MAIL_SERVER'),
                    'mail_port': current_app.config.get('MAIL_PORT'),
                    'mail_security': current_app.config.get('MAIL_SECURITY'),
                    'mail_username': current_app.config.get('MAIL_DEFAULT_SENDER'),
                    'mail_password': current_app.config.get('MAIL_PASSWORD'),})
    # cache.clear()


@admin_bp.before_request
def update_last_seen():
    """
    Update when the current user was last seen (User.last_seen attribute).
    """
    if current_user.is_authenticated:
        current_user.user_seen()
        db.session.commit()


def background_job():
    """
    Run process in background.
    """
    with scheduler.app.app_context():
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        # only for tests
        # print(today)    # only for tests
        events_to_notify = Event.query.filter(Event.time_notify <= today,
                                              Event.is_active == True,
                                              Event.to_notify == True,
                                              Event.notification_sent == False).all()
        try:
            for event in events_to_notify:
                users_to_notify = [user for user in event.notified_users]
                users_notified = smtp_mail.send_email('Attention! Upcoming event!',
                                     users_to_notify,
                                     event,
                                     cache.get('mail_server'),
                                     cache.get('mail_port'),
                                     cache.get('mail_security'),
                                     cache.get('mail_username'),
                                     cache.get('mail_password'))
                current_app.logger_admin.info(f'Notification service: notification has been sent to: {users_notified}')
                # only for test
                # print(f'Mail sent to {users_notified}')
                event.notification_sent = True
            db.session.commit()
        except Exception as error:
            current_app.logger_admin.error(f'Background job error: {error}')
            # Remove job when error occure.
            scheduler.remove_job('my_job_id')


@admin_bp.route('/events')
@login_required
@admin_required
def events():
    """
    Display all events from db in Admin Portal.
    """
    # Pagination
    events_per_page = 10
    page = request.args.get('page', 1, type=int)

    if not request.args or (request.args.get('col') == 'start' and request.args.get('dir') == 'asc'):
        events = Event.query.order_by("time_event_start").paginate(page, events_per_page, True)
    elif request.args.get('col') == 'id' and request.args.get('dir') == 'desc':
        events = Event.query.order_by(desc(Event.id)).paginate(page, events_per_page, True)
    elif request.args.get('col') == 'id' and request.args.get('dir') == 'asc':
        events = Event.query.order_by(asc(Event.id)).paginate(page, events_per_page, True)
    elif request.args.get('col') == 'start' and request.args.get('dir') == 'desc':
        events = Event.query.order_by(desc(Event.time_event_start)).paginate(page, events_per_page, True)
    elif request.args.get('col') == 'start' and request.args.get('dir') == 'asc':
        events = Event.query.order_by(asc(Event.time_event_start)).paginate(page, events_per_page, True)
    elif request.args.get('col') == 'stop' and request.args.get('dir') == 'desc':
        events = Event.query.order_by(desc(Event.time_event_stop)).paginate(page, events_per_page, True)
    elif request.args.get('col') == 'stop' and request.args.get('dir') == 'asc':
        events = Event.query.order_by(asc(Event.time_event_stop)).paginate(page, events_per_page, True)
    elif request.args.get('col') == 'title' and request.args.get('dir') == 'asc':
        events = Event.query.order_by(func.lower(Event.title).asc()).paginate(page, events_per_page, True)
    elif request.args.get('col') == 'title' and request.args.get('dir') == 'desc':
        events = Event.query.order_by(func.lower(Event.title).desc()).paginate(page, events_per_page, True)
    elif request.args.get('col') == 'notify' and request.args.get('dir') == 'yes':
        events = Event.query.filter(Event.to_notify == True).order_by("time_event_start")\
            .paginate(page, events_per_page, True)
    elif request.args.get('col') == 'notify' and request.args.get('dir') == 'no':
        events = Event.query.filter(Event.to_notify == False).order_by("time_event_start")\
            .paginate(page, events_per_page, True)
    elif request.args.get('col') == 'active' and request.args.get('dir') == 'no':
        events = Event.query.filter(Event.is_active == False).order_by("time_event_start")\
            .paginate(page, events_per_page, True)
    elif request.args.get('col') == 'active' and request.args.get('dir') == 'yes':
        events = Event.query.filter(Event.is_active == True).order_by("time_event_start")\
            .paginate(page, events_per_page, True)
    else:
        abort(404)
    # Remember additional URL in session, if last event on page - for event deleting feature
    if session.get('prev_endpoint_del'):
        del session['prev_endpoint_del']
    if len(events.items) == 1 and not page == 1:
        session['prev_endpoint_del'] = url_for('admin_bp.events',
                                           col=request.args.get('col'),
                                           dir=request.args.get('dir'),
                                           page=page - 1)
    # Remember current url in session (for back-redirect)
    if not request.args:
        session['prev_endpoint'] = url_for('admin_bp.events')
    else:
        session['prev_endpoint'] = url_for('admin_bp.events',
                                           col=request.args.get('col'),
                                           dir=request.args.get('dir'),
                                           page=page)
    # URLs for pagination navigation
    next_url = url_for('admin_bp.events',
                       col=request.args.get('col', 'start'),
                       dir=request.args.get('dir', 'asc'),
                       page=events.next_num) if events.has_next else None
    prev_url = url_for('admin_bp.events',
                       col=request.args.get('col', 'start'),
                       dir=request.args.get('dir', 'asc'),
                       page=events.prev_num) if events.has_prev else None
    return render_template('admin/events.html',
                           events=events,
                           title='Events', next_url=next_url,
                           prev_url=prev_url,
                           events_per_page=events_per_page)


@admin_bp.route('/event/<int:event_id>', methods=['GET', 'POST'])
@cancel_click()
@login_required
@admin_required
def event(event_id):
    """
    Display particular event's details.
    The event details in Admin Portal.
    """
    event = Event.query.filter_by(id=event_id).first_or_404()
    # Fetch users that can be notified (only with user role)
    users_to_notify = User.get_all_standard_users()
    today = datetime.date.today().strftime("%Y-%m-%d")
    if request.method == "POST":
        event.title = request.form.get('title')
        event.details = request.form.get('details')
        event.all_day_event = True if request.form.get('allday') == 'True' else False
        event.to_notify = True if request.form.get('to_notify') == 'True' else False
        if request.form.get('date_notify'):
            event.time_notify = main_views.str_to_datetime(request.form.get('date_notify'),
                                                     request.form.get('time_notify'))
        else:
            event.time_notify = None
        event.notification_sent = True if request.form.get('notify_sent') == 'True' else False
        # Check if event ia all_day event or not.
        if request.form.get('time_event_start'):
            time_event_start_db = main_views.str_to_datetime(request.form.get('date_event_start'),
                                                  request.form.get('time_event_start'))
            time_event_stop_db = main_views.str_to_datetime(request.form.get('date_event_stop'),
                                                 request.form.get('time_event_stop'))
        else:
            time_event_start_db = main_views.str_to_datetime(request.form.get('date_event_start'))
            time_event_stop_db = main_views.str_to_datetime(request.form.get('date_event_stop'))
        event.time_event_start = time_event_start_db
        event.time_event_stop = time_event_stop_db
        # Set users to notify. If "to_notify = False" the list "user_form" is []
        users_form = request.form.getlist('notified_user')
        # Overwrite current users to notify.
        event.notified_users = [User.query.get(user_id) for user_id in users_form]
        db.session.commit()
        flash('Your changes have been saved!', 'success')
        if 'prev_endpoint' in session:
            return redirect(session['prev_endpoint'])
        return redirect(url_for('admin_bp.events'))
    return render_template('admin/event.html', event=event, title='Event details', users=users_to_notify, today=today)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """
    List user's data from db in Admin Portal.
    """
    # Pagination
    users_per_page = 10
    page = request.args.get('page', 1, type=int)
    # Remember current url in session (for back-redirect)
    session['prev_endpoint'] = url_for('admin_bp.users',
                                       page=request.args.get('page'))
    users = User.query.order_by(func.lower(User.username).asc()).paginate(page, users_per_page, True)
    # URLs for pagination navigation
    next_url = url_for('admin_bp.users',
                       page=users.next_num) if users.has_next else None
    prev_url = url_for('admin_bp.users',
                       page=users.prev_num) if users.has_prev else None

    return render_template('admin/users.html',
                           users=users,
                           title='Users',
                           prev_url=prev_url,
                           next_url=next_url,
                           users_per_page=users_per_page)


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
        pass_reset_from_form = True if request.form.get('pass_reset') == 'True' else False
        form_content = {
            'username': username_from_form,
            'email': email_from_form,
            'access': access_from_form,
            'roleid': True if roleid_from_form == 'admin' else False,
            'pass_reset': pass_reset_from_form,
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
@cancel_click('admin_bp.users')
@login_required
@admin_required
def new_user():
    """
    Add new user to db.
    """
    if request.method == "POST":
        form = NewUserForm()
        # Validate form data on server-side
        if form.validate_on_submit():
            # Check if username and email already exist in db.
            user_exist = check_user_exist(request)
            if user_exist:
                return render_template('admin/new_user.html', title='New user', form_content=user_exist)
            username_form = request.form.get('username')
            email_form = request.form.get('email')
            password_form = request.form.get('password')
            user = User(username=username_form,
                        email=email_form,
                        access_granted=True if request.form.get('access') == 'True' else False,
                        pass_change_req=True if request.form.get('pass_reset') == 'True' else False,
                        role_id=str(Role.query.filter_by(name=request.form.get('role')).first().id))
            user.set_password(password_form)
            db.session.add(user)
            db.session.commit()
            current_app.logger_admin.info(f'User "{user.username}" has been added to db')
            flash(f'User "{user.username}" has been added!', 'success')
            return redirect(url_for('admin_bp.users'))
        if form.errors:
            flash_errors(form)
            # Render previous user input in form fields
            return render_template('admin/new_user.html', title='New user', form_prev_input=form)
    return render_template('admin/new_user.html', title='New user')


@admin_bp.route('/user/<int:user_id>', methods=['GET', 'POST'])
@cancel_click()
@login_required
@admin_required
def user(user_id):
    """
    Editing an user already existing in the db.
    """
    user = User.query.filter_by(id=user_id).first_or_404()
    if request.method == "POST":
        form = EditUserForm()
        # Validate form data on server-side
        if form.validate_on_submit():
            # Check if new assigned username or email exist in db.
            user_exist = check_user_exist(request, user)
            if user_exist:
                return render_template('admin/user.html', user=user)
            username_form = request.form.get('username')
            email_form = request.form.get('email')
            password_form = request.form.get('password')
            user.username = username_form
            user.email = email_form
            if request.form.get('access') == 'True' and str(user.access_granted) != request.form.get('access'):
                user.failed_login_attempts = 0
            user.access_granted = True if request.form.get('access') == 'True' else False
            user.pass_change_req = True if request.form.get('pass_reset') == 'True' else False
            user.role_id = str(Role.query.filter_by(name=request.form.get('role')).first().id)
            # Check whether password has been changed
            if password_form and not user.check_password(password_form):
                user.set_password(password_form)
            db.session.commit()
            current_app.logger_admin.info(f'User "{user.username}" data has been changed')
            flash('Your changes have been saved!', 'success')
            return redirect(url_for('admin_bp.users'))
        if form.errors:
            flash_errors(form)
            # Render previous user input in form fields
            return render_template('admin/user.html', form_prev_input=form)
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
    current_app.logger_admin.warning(f'User "{user.username} has been deleted from db"')
    db.session.delete(user)
    db.session.commit()
    flash(f'User "{user.username}" has been deleted!', 'success')
    if 'prev_endpoint' in session:
        return redirect(session['prev_endpoint'])
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
    # Custom small delay when deleting search results from db (for elasticsearch better performance)
    if 'search' in session.get('prev_endpoint'):
        time.sleep(1)
    if session.get('prev_endpoint_del'):
        return redirect(session.get('prev_endpoint_del'))
    elif session.get('prev_endpoint'):
        return redirect(session['prev_endpoint'])
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
    # Redirect to previous URL
    if 'prev_endpoint' in session:
        return redirect(session['prev_endpoint'])
    return redirect(url_for('admin_bp.events'))


@admin_bp.route('/notify/', methods=['GET', 'POST'])
@cancel_click('admin_bp.dashboard')
@login_required
@admin_required
def notify():
    """
    Func allows to start notification service and change the service configuration.
    """
    # only for test
    # print(scheduler.get_jobs(jobstore='default'))
    # Get mail config from cache
    mail_config_cache = cache.get_dict('mail_server',
                                       'mail_port',
                                       'mail_security',
                                       'mail_username',
                                       'mail_password')
    # Notification config data (for interval and interval unit).
    notification_config = Notification.query.first()
    # Mail config data.
    notify_config = mail_config_cache.copy()
    notify_config['notify_unit'] = notification_config.notify_unit
    notify_config['notify_interval'] = notification_config.notify_interval
    if request.method == "POST":
        form = NotifyForm()
        # Validate form data on server-side
        if form.validate_on_submit():
            # Fetch data from form.
            notify_status_form = request.form.get('notify_status')
            notify_unit_form = request.form.get('notify_unit')
            notify_interval_form = int(request.form.get('notify_interval'))
            # Checks whether the data provided in the form differs from those stored in the cache
            # and update the data in 'notify_config' div and config object (if required).
            config_changed = False
            for key, val in notify_config.items():
                if key in form.data.keys() and key in mail_config_cache.keys():
                    if notify_config[key] != str(form.data[key]) and str(form.data[key]) != '':
                        cache.set(key, str(form.data[key]))
                        notify_config[key] = str(form.data[key])
                        config_changed = True
                        print(key, form.data[key])
            # Checks whether the data provided in the form differs from those stored in the db
            if notify_unit_form != notify_config['notify_unit'] or \
                    notify_interval_form != notify_config['notify_interval']:
                notification_config.notify_unit = notify_unit_form
                notification_config.notify_interval = notify_interval_form
                db.session.commit()
                # Update the rest of the data in 'notify_config' dic.
                notify_config['notify_unit'] = notify_unit_form
                notify_config['notify_interval'] = notify_interval_form
                config_changed = True
                print(notify_config)
            print(config_changed)
            # Test mail configuration before running service
            if notify_status_form == 'on':
                test_mail_config = smtp_mail.test_email(notify_config['mail_server'],
                                                        notify_config['mail_port'],
                                                        notify_config['mail_security'],
                                                        notify_config['mail_username'],
                                                        notify_config['mail_password'])
            else:
                test_mail_config = False
            # Notification service engine
            if not notify_status_form and scheduler.get_jobs():
                scheduler.remove_job('my_job_id')
                current_app.logger_admin.info(f'Notification service has been turned off by "{current_user.username}"')
                flash('The notify service has been turned off!', 'success')
            elif scheduler.get_jobs() and not test_mail_config:
                scheduler.remove_job('my_job_id')
            elif notify_status_form == 'on' and test_mail_config:
                if not scheduler.get_jobs():
                    current_app.logger_admin.info(f'Notification service has been started by "{current_user.username}"')
                else:
                    current_app.logger_admin.info(f'Notification service config has been changed by '
                                                  f'"{current_user.username}"')
                if notify_unit_form == 'seconds':
                    scheduler.add_job(func=background_job, trigger='interval', replace_existing=True, max_instances=1,
                                      seconds=notify_interval_form, id='my_job_id')
                elif notify_unit_form == 'minutes':
                    scheduler.add_job(func=background_job, trigger='interval', replace_existing=True, max_instances=1,
                                      minutes=notify_interval_form, id='my_job_id')
                else:
                    scheduler.add_job(func=background_job, trigger='interval', replace_existing=True, max_instances=1,
                                      hours=notify_interval_form, id='my_job_id')
                flash('Connection with mail server established correctly! The notify service is running!', 'success')
            # Flash msg when config has been changed by user
            if not scheduler.get_jobs() and config_changed:
                current_app.logger_admin.info(f'Notification service config has been changed by '
                                              f'"{current_user.username}"')
                flash('The notification service config has been changed!', 'success')
        if form.errors:
            flash_errors(form)
    # Determine weather some scheduler jobs exist - if True, notification service is running
    service_run = True if scheduler.get_jobs() else False
    return render_template('admin/notify.html', service_run=service_run, **notify_config)


@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    """
    List app's logs.
    """
    logs_per_page = 12
    page = request.args.get('page', 1, type=int)
    if not request.args or (request.args.get('col') == 'time' and request.args.get('dir') == 'desc'):
        logs = Log.query.order_by(desc(Log.time)).paginate(page, logs_per_page, True)
    elif request.args.get('col') == 'time' and request.args.get('dir') == 'desc':
        logs = Log.query.order_by(desc(Log.time)).paginate(page, logs_per_page, True)
    elif request.args.get('col') == 'time' and request.args.get('dir') == 'asc':
        logs = Log.query.order_by(asc(Log.time)).paginate(page, logs_per_page, True)
    elif request.args.get('col') == 'log_name' and request.args.get('dir') == 'desc':
        logs = Log.query.order_by(desc(Log.log_name)).paginate(page, logs_per_page, True)
    elif request.args.get('col') == 'log_name' and request.args.get('dir') == 'asc':
        logs = Log.query.order_by(asc(Log.log_name)).paginate(page, logs_per_page, True)
    elif request.args.get('col') == 'level' and request.args.get('dir') == 'asc':
        logs = Log.query.order_by(asc(Log.level)).paginate(page, logs_per_page, True)
    elif request.args.get('col') == 'level' and request.args.get('dir') == 'desc':
        logs = Log.query.order_by(desc(Log.level)).paginate(page, logs_per_page, True)
    else:
        abort(404)
    if not request.args:
        session['prev_endpoint'] = url_for('admin_bp.logs')
    else:
        session['prev_endpoint'] = url_for('admin_bp.logs',
                                           col=request.args.get('col'),
                                           page=page)
    next_url = url_for('admin_bp.logs',
                       col=request.args.get('col', 'time'),
                       dir=request.args.get('dir', 'desc'),
                       page=logs.next_num) if logs.has_next else None
    prev_url = url_for('admin_bp.logs',
                       col=request.args.get('col', 'time'),
                       dir=request.args.get('dir', 'desc'),
                       page=logs.prev_num) if logs.has_prev else None
    return render_template('admin/logs.html',
                           logs=logs,
                           next_url=next_url,
                           prev_url=prev_url,
                           logs_per_page=logs_per_page)


@admin_bp.route('/logs_clear')
@login_required
@admin_required
def logs_clear():
    """
    Clear app's logs.
    """
    if request.args.get('range') == 'all':
        db.session.query(Log).delete()
        db.session.commit()
    elif request.args.get('range') == 'day1':
        Log.delete_expired(1)
    elif request.args.get('range') == 'week1':
        Log.delete_expired(7)
    elif request.args.get('range') == 'week2':
        Log.delete_expired(14)
    elif request.args.get('range') == 'month1':
        Log.delete_expired(31)
    elif request.args.get('range') == 'month3':
        Log.delete_expired(90)
    else:
        abort(404)
    flash('Logs from the selected timeframe have been deleted!', 'success')
    return redirect(url_for('admin_bp.logs'))


@admin_bp.route('/search_engine', methods=['GET', 'POST'])
@cancel_click('admin_bp.dashboard')
@login_required
@admin_required
def search_engine():
    """
    View shows search engine's status and config in admin dashboard.
    """
    search_service_status = False if not current_app.elasticsearch or not current_app.elasticsearch.ping() else True
    search_url = current_app.config.get('ELASTICSEARCH_URL')
    # Get elasticsearch node info
    search_config_data = {}
    if search_service_status:
        response = requests.get(search_url)
        search_config_data = json.loads(response.text)
    if search_config_data.get('version'):
        search_service_version = search_config_data.get('version').get('number', 'No data')
        search_service_build_type = search_config_data.get('version').get('build_type', 'No data')
    else:
        search_service_version = search_config_data.get('version', 'No data')
        search_service_build_type = search_config_data.get('version', 'No data')
    search_config = {
        'search_url': search_url,
        'search_service_status': search_service_status,
        'search_service_version': search_service_version,
        'search_service_build_type': search_service_build_type,
    }
    if request.method == "POST":
        # Reindex on demand - add all events and logs from the db to the search index in elasticsearch.
        Event.reindex()
        Log.reindex()
        flash(f'Data from database have been reindexed!', 'success')
    return render_template('admin/search_engine.html', **search_config)


@admin_bp.route('/search')
@login_required
@admin_required
def search():
    """
    Search engine for admin blueprint.
    """
    if not current_app.elasticsearch or not current_app.elasticsearch.ping():
        flash(f'Sorry! No connection with search engine!', 'danger')
        return redirect(session.get('prev_endpoint'))
    # Fetch all current event's authors from db.
    page = request.args.get('page', 1, type=int)
    items_per_page = 10
    try:
        if request.args.get('sub') == 'events':
            events, total = Event.search(request.args.get('q'), page, items_per_page)
            items_on_current_page = events.count()
        elif request.args.get('sub') == 'logs':
            logs, total = Log.search(request.args.get('q'), page, items_per_page)
            items_on_current_page = logs.count()
        else:
            abort(404)
    except (elasticsearch.exceptions.RequestError, TypeError):
        abort(404)
    next_url = url_for('admin_bp.search', sub=request.args.get('sub'), q=request.args.get('q'), page=page + 1) \
        if total > page * items_per_page else None
    prev_url = url_for('admin_bp.search', sub=request.args.get('sub'), q=request.args.get('q'), page=page - 1) \
        if page > 1 else None
    # Pagination for search results
    page_last = int(total / items_per_page) + 1 if (total / items_per_page % 1) != 0 else int(total / items_per_page)
    pagination = {
        'page_first': 1,
        'page_current': page,
        'page_last': page_last,
        'page_prev': page - 1 if page > 1 else None,
        'page_next': page + 1 if total > page * items_per_page else None,
        'items_per_page': items_per_page,
    }
    # Remember additional URL in session, if there is only one event on page - for event deactivation feature
    if session.get('prev_endpoint_del'):
        del session['prev_endpoint_del']
    if items_on_current_page == 1 and not page == 1:
        session['prev_endpoint_del'] = url_for('admin_bp.search',
                                               sub=request.args.get('sub'),
                                               q=request.args.get('q'),
                                               page=page - 1)
    # Remember current url in session (for back-redirect)
    if not request.args.get('page'):
        session['prev_endpoint'] = url_for('admin_bp.search',
                                           sub=request.args.get('sub'),
                                           q=request.args.get('q'))
    else:
        session['prev_endpoint'] = url_for('admin_bp.search',
                                           sub=request.args.get('sub'),
                                           q=request.args.get('q'),
                                           page=request.args.get('page'))
    if request.args.get('sub') == 'events':
        return render_template('admin/search.html',
                               title='Search',
                               events=events,
                               total=total,
                               next_url=next_url,
                               prev_url=prev_url,
                               **pagination)
    elif request.args.get('sub') == 'logs':
        return render_template('admin/search.html',
                               title='Search',
                               logs=logs,
                               total=total,
                               next_url=next_url,
                               prev_url=prev_url,
                               **pagination)


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Data fetched from db
    users_count = User.query.count()
    standard_users_count = User.query.filter(User.role_id == 2).count()
    admin_users_count = User.query.filter(User.role_id == 1).count()
    events_active = Event.query.filter(Event.is_active == True).count()
    events_notactive = Event.query.filter(Event.is_active == False).count()
    events_count = Event.query.count()
    # Data for chart - 'Events created in last 30 days'
    today = datetime.datetime.today()
    events = Event.query.with_entities(Event.time_creation).filter(Event.time_creation <= today,
                                Event.time_creation >= today - datetime.timedelta(days=31)).order_by('time_creation').all()
    event_dates = [event[0].date() for event in events]
    chart_data = {}
    for day in event_dates:
        new = chart_data.get(day, 0)
        chart_data[day] = new + 1
    events_labels = chart_data.keys()
    events_values = chart_data.values()

    if not current_app.elasticsearch or not current_app.elasticsearch.ping():
        search_status = False
    else:
        search_status = True
    notification_status = True if scheduler.get_jobs() else False
    data = {
        'users_count': users_count,
        'standard_users_count': standard_users_count,
        'admin_users_count': admin_users_count,
        'events_count': events_count,
        'search_status': search_status,
        'notification_status': notification_status,
        'events_active': events_active,
        'events_notactive': events_notactive,
        'events_labels': list(events_labels),
        'events_values': list(events_values),
    }
    return render_template('admin/dashboard.html', **data)
