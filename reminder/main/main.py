from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort, current_app
from reminder import db, scheduler
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from reminder.models import User, Event, Role
from werkzeug.exceptions import HTTPException
from sqlalchemy import func, or_, and_
import datetime
from reminder.admin.admin import admin_required
import logging


main_bp = Blueprint('main_bp', __name__,
                    template_folder='templates',
                    static_folder='static')


def str_to_datetime(date_str, time_str=None):
    """
    Convert date string (format ISO 2020-01-02 or 2020-01-02T10:00) to datetime.datetime object
    """
    if not time_str:
        return datetime.datetime.fromisoformat(date_str)
    return datetime.datetime.fromisoformat(f'{date_str}T{time_str}')


def event_process(event):
    """
    Fetch and process event data for event edition

    """
    pass


@main_bp.before_request
def update_last_seen():
    """
    Update when the current user was last seen (User.last_seen attribute).
    """
    if request.method == "POST":    # only for tests
        print(request.form)
    if current_user.is_authenticated:
        current_user.user_seen()
        db.session.commit()


@main_bp.route('/')
@main_bp.route('/index')
def index():
    """
    Display all events on FullCalendar.
    """
    # current_app.logger.error('Test')
    events = Event.query.all()
    return render_template('index.html', events=events, title='Home')


@main_bp.route('/admin_portal')
@login_required
@admin_required
def admin_portal():
    """
    Portal for user with admin rights.
    """
    return redirect(url_for('admin_bp.users'))


@main_bp.route('/events_list')
def events_list():
    """
    Display all events in list format.
    """
    today = datetime.datetime.today()

    # Fetch all current event's authors from db.
    author_ids = set([_.author_uid for _ in Event.query.filter(and_(or_(Event.time_event_start >= today,
                                                                        Event.time_event_stop >= today)),
                                                               Event.is_active == True, ).all()])
    users = User.query.filter(User.role_id == 2).order_by(func.lower(User.username).asc()).all()
    # Check whether user is author (prepare list of authors)
    event_authors = [user for user in users if user.id in author_ids]
    if not request.args or request.args.get('list') == 'current':
        # Show only active events:
        events = Event.query.filter(and_(or_(Event.time_event_start >= today,
                                             Event.time_event_stop >= today)),
                                    Event.is_active == True).order_by("time_event_start").all()
    elif request.args.get('list') == 'own':
        # Show only current user events.
        events = Event.query.filter(and_(or_(Event.time_event_start >= today,
                                             Event.time_event_stop >= today)),
                                    Event.is_active == True, Event.author == current_user)\
            .order_by("time_event_start").all()
    elif request.args.get('list') == 'all':
        # Show ALL events (current and old events)
        events = Event.query.filter(Event.is_active == True).order_by("time_event_start").all()
    elif request.args.get('list') == 'author' and int(request.args.get('id')) in author_ids:
        # Show current events by user.
        events = Event.query.filter(and_(or_(Event.time_event_start >= today, Event.time_event_stop >= today)),
                                    Event.is_active == True,
                                    Event.author_uid == request.args.get('id')).order_by("time_event_start").all()
    else:
        abort(404)
    return render_template('events_list.html', events=events, title='List', today=today, event_authors=event_authors)


@main_bp.route('/api/events')
def get_events():
    """
    API for FullCalendar.
    """
    today = datetime.datetime.today()
    # how to limit huge number of API request???????? DDoS/DoS mitigation????
    date_start, date_end = request.args['start'], request.args['end']

    # Create datetime objects for calendar view date limits.
    try:
        date_start_dt = datetime.datetime(int(date_start[:4]), int(date_start[5:7]), int(date_start[8:10]))
        date_end_dt = datetime.datetime(int(date_end[:4]), int(date_end[5:7]), int(date_end[8:10]))
        # Fetch all events for current calendar view (with 'is_active=True').
        events = Event.query.filter(Event.time_event_start >= date_start_dt,
                                    Event.time_event_start <= date_end_dt,
                                    Event.is_active == True).all()
    except ValueError:
        abort(404)
    events_api = []
    for event in events:
        if event.time_event_start >= today:
            background_color = 'blue'
            border_color = 'blue'
        elif event.time_event_stop >= today:
            background_color = 'green'
            border_color = 'green'
        else:
            background_color = 'red'
            border_color = 'red'

        event_dic = {
            'id': event.id,
            'title': event.title,
            'start': event.time_event_start.isoformat(),      # ISO format '2020-04-12T14:30:00'
            'end': event.time_event_stop.isoformat(),
            'allDay': event.all_day_event,
            'backgroundColor': background_color,
            'borderColor': border_color,
            'extendedProps': {
                "details": event.details,
            },
        }
        events_api.append(event_dic)
    return jsonify(events_api)


@main_bp.route('/new_event', methods=['GET', 'POST'])
@login_required
def new_event():
    """
    Add new event to db.
    """
    # print(request.form.getlist('notified_user'))
    # notified_uids = request.form.getlist('notified_user')
    users_to_notify = User.query.filter_by(role_id=2).all()
    today = datetime.date.today().strftime("%Y-%m-%d")
    if request.method == "POST":
        # If a "Cancel" button has been pressed.
        if request.form.get('cancel-btn') == 'Cancel':
            return redirect(url_for('main_bp.index'))
        to_notify_db = True if request.form.get('to_notify') == 'True' else False
        time_notify_db = str_to_datetime(request.form.get('date_notify'), request.form.get('time_notify')) \
            if request.form.get('date_notify') else None
        # Check if all day event or not.
        if request.form.get('time_event_start'):
            time_event_start_db = str_to_datetime(request.form.get('date_event_start'),
                                                  request.form.get('time_event_start'))
            time_event_stop_db = str_to_datetime(request.form.get('date_event_stop'),
                                                  request.form.get('time_event_stop'))
        else:
            time_event_start_db = str_to_datetime(request.form.get('date_event_start'))
            time_event_stop_db = str_to_datetime(request.form.get('date_event_stop'))

        event = Event(title=request.form.get('title'),
                      details=request.form.get('details'),
                      all_day_event=True if request.form.get('allday') == 'True' else False,
                      time_event_start=time_event_start_db,
                      time_event_stop=time_event_stop_db,
                      to_notify=to_notify_db,
                      time_notify=time_notify_db,
                      author_uid=current_user.id
                      )
        db.session.add(event)
        db.session.commit()
        # assign user
        users_form = request.form.getlist('notified_user')
        for user_id in users_form:
            user = User.query.get(user_id)
            user.events_notified.append(event)
            db.session.add(user)
        db.session.commit()
        flash('New event has been added!', 'success')
        return redirect(url_for('main_bp.index'))
    return render_template('new_event.html', title='New event', users=users_to_notify, today=today)


@main_bp.route('/event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def event(event_id):
    """
    Editing an event already existing in the db.
    """
    event = Event.query.filter_by(id=event_id).first_or_404()
    # Fetch users that can be notified (only with user role)
    users_to_notify = User.query.filter_by(role_id=2).all()
    today = datetime.date.today().strftime("%Y-%m-%d")

    if request.method == "POST":
        # If a "Cancel" button has been pressed.
        if request.form.get('cancel-btn') == 'Cancel':
            return redirect(url_for('main_bp.events_list'))

        event.title = request.form.get('title')
        event.details = request.form.get('details')

        event.to_notify = True if request.form.get('to_notify') == 'True' else False
        event.time_notify = str_to_datetime(request.form.get('date_notify'), request.form.get('time_notify')) \
            if request.form.get('date_notify') else None
        event.all_day_event = True if request.form.get('allday') == 'True' else False

        # Check if all day event or not.
        if request.form.get('time_event_start'):
            time_event_start_db = str_to_datetime(request.form.get('date_event_start'),
                                                  request.form.get('time_event_start'))
            time_event_stop_db = str_to_datetime(request.form.get('date_event_stop'),
                                                 request.form.get('time_event_stop'))
        else:
            time_event_start_db = str_to_datetime(request.form.get('date_event_start'))
            time_event_stop_db = str_to_datetime(request.form.get('date_event_stop'))
        event.time_event_start = time_event_start_db
        event.time_event_stop = time_event_stop_db

        # Set users to notify. If "to_notify = False" the list "user_form" is []
        users_form = request.form.getlist('notified_user')
        # Overwrite current users to notify.
        event.notified_uids = [User.query.get(user_id) for user_id in users_form]
        db.session.commit()
        flash('Your changes have been saved!', 'success')
        return redirect(url_for('main_bp.events_list'))
    return render_template('event.html', event=event, title='Edit event', users=users_to_notify, today=today)


@main_bp.route('/dea_event/<int:event_id>')
@login_required
def deactive_event(event_id):
    """
    Remove event from 'events_list' - deactivate event.
    """
    event = Event.query.filter_by(id=event_id).first()
    if (current_user.id != event.author.id) and (not current_user.is_admin()):
        flash("Sorry! You can't delete someone's event!", 'danger')
        return redirect(url_for('main_bp.events_list'))
    event.is_active = False
    db.session.commit()
    flash(f'Event with title "{event.title}" has been deleted!', 'success')
    return redirect(url_for('main_bp.events_list'))


@main_bp.route('/about')
def about():
    return render_template('about.html', title='About')


@main_bp.app_errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@main_bp.app_errorhandler(HTTPException)
def handle_bad_request(error):
    return render_template('404.html'), 400


@main_bp.app_errorhandler(500)
def internal_server_error(error):
    return render_template('500.html'), 500



