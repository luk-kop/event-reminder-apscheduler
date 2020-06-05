import datetime
import time

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort, current_app, session
from flask_login import current_user
from werkzeug.exceptions import HTTPException
from sqlalchemy import func, or_, and_
import elasticsearch.exceptions

from reminder.extensions import db
from reminder.models import User, Event
from reminder.custom_decorators import admin_required, login_required, cancel_click
from reminder.admin.views import test_pattern


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


@main_bp.before_request
def update_last_seen():
    """
    Update when the current user was last seen (User.last_seen attribute).
    """
    if current_user.is_authenticated:
        current_user.user_seen()
        db.session.commit()


@main_bp.route('/')
@main_bp.route('/index')
def index():
    """
    Display all events on FullCalendar.
    """
    events = Event.query.all()
    return render_template('index.html', events=events, title='Home')


@main_bp.route('/admin_portal')
@login_required
@admin_required
def admin_portal():
    """
    Portal for user with admin rights.
    """
    return redirect(url_for('admin_bp.dashboard'))


def events_authors_func(today, today_only_day):
    """
    Fetch all current event's authors from db
    """
    author_ids = set([_.author_uid for _ in Event.query.filter(and_(or_(Event.time_event_start >= today,
                                                                        Event.time_event_stop >= today,
                                                                        and_(Event.all_day_event == True,
                                                                             Event.time_event_stop == today_only_day))),
                                                               Event.is_active == True, ).all()])
    users = User.query.filter(User.role_id == 2).order_by(func.lower(User.username).asc()).all()
    # Check whether user is author (prepare list of authors)
    event_authors = [user for user in users if user.id in author_ids]
    return event_authors, author_ids


@main_bp.route('/events_list')
def events_list():
    """
    Display all events in list format.
    """
    today = datetime.datetime.today()
    today_only_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
    page = request.args.get('page', 1, type=int)
    events_per_page = 10
    # Fetch all current event's authors from db.
    event_authors, author_ids = events_authors_func(today, today_only_day)
    # Get 'author_id' from query param
    author_id = request.args.get('id', type=int)
    if not request.args or request.args.get('list') == 'current':
        # Show only active events:
        events = Event.query.filter(
            and_(or_(Event.time_event_start >= today,
                     Event.time_event_stop >= today,
                     and_(Event.all_day_event == True,
                          Event.time_event_stop == today_only_day))),
            Event.is_active == True).order_by("time_event_start").paginate(page, events_per_page, True)
    elif request.args.get('list') == 'own':
        if not current_user.is_authenticated:
            abort(404)
        events = Event.query.filter(
            and_(or_(Event.time_event_start >= today,
                     Event.time_event_stop >= today,
                     and_(Event.all_day_event == True, Event.time_event_stop == today_only_day))),
            Event.is_active == True, Event.author == current_user).order_by("time_event_start") \
            .paginate(page, events_per_page, True)
    elif request.args.get('list') == 'all':
        # Show ALL events (current and old events)
        events = Event.query.filter(Event.is_active == True).order_by("time_event_start") \
            .paginate(page, events_per_page, True)
    elif request.args.get('list') == 'author' and author_id in author_ids:
        # Show current events by user.
        events = Event.query.filter(
            and_(or_(Event.time_event_start >= today,
                     Event.time_event_stop >= today,
                     and_(Event.all_day_event == True,
                          Event.time_event_stop == today_only_day))),
            Event.is_active == True,
            Event.author_uid == str(author_id)).order_by("time_event_start").paginate(page, events_per_page, True)
    elif request.args.get('list') == 'author' and author_id not in author_ids:
        return redirect(url_for('main_bp.events_list'))
    else:
        abort(404)
    # URLs for pagination navigation
    next_url = url_for('main_bp.events_list',
                       list=request.args.get('list', 'current'),
                       id=request.args.get('id'),
                       page=events.next_num) if events.has_next else None
    prev_url = url_for('main_bp.events_list',
                       list=request.args.get('list', 'current'),
                       id=request.args.get('id'),
                       page=events.prev_num) if events.has_prev else None
    # Remember additional URL in session, if last event on page - for event deactivation feature
    if session.get('prev_endpoint_dea'):
         del session['prev_endpoint_dea']
    events_on_current_page = len(events.items)
    if events_on_current_page == 1 and not page == 1:
        session['prev_endpoint_dea'] = url_for('main_bp.events_list',
                                           list=request.args.get('list'),
                                           id=request.args.get('id'),
                                           page=page - 1)
    # Remember current url in session (for back-redirect)
    if not request.args:
        session['prev_endpoint'] = url_for('main_bp.events_list')
    else:
        session['prev_endpoint'] = url_for('main_bp.events_list',
                                            list=request.args.get('list'),
                                            id=request.args.get('id'),
                                            page=page)
    return render_template('events_list.html',
                           events=events,
                           title='List',
                           today=today,
                           today_only_day=today_only_day,
                           event_authors=event_authors,
                           next_url=next_url,
                           prev_url=prev_url)


@main_bp.route('/api/events')
def get_events():
    """
    API for FullCalendar.
    """
    today = datetime.datetime.today()
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
        elif event.time_event_stop >= today or (event.all_day_event and event.time_event_stop.date() == today.date()):
            background_color = 'green'
            border_color = 'green'
        else:
            background_color = 'red'
            border_color = 'red'

        event_dic = {
            'id': event.id,
            'title': event.title,
            'start': event.time_event_start.isoformat(), # ISO format '2020-04-12T14:30:00'
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


def event_validation(request):
    """
    Validate user input on server-side
    """
    print(request.form)
    title_form = request.form.get('title')
    date_event_start_form = request.form.get('date_event_start')
    date_event_stop_form = request.form.get('date_event_stop')
    date_event_notify_form = request.form.get('date_notify')
    pattern_date = r'^\d{4}-(0[1-9]|[1][0-2])-(0[1-9]|1[0-9]|2[0-9]|3[0-1])$'

    # date_event_start, date_event_start, date_notify, 2020-05-26
    # pattern_username = r'^[a-zA-Z0-9][a-zA-Z0-9\._-]{3,40}$'
    if not title_form or len(title_form) > Event.title.type.length:
        flash(f'Please enter event\'s title!', 'danger')
        return False
    if not date_event_start_form or not test_pattern(pattern_date, date_event_start_form):
        flash(f'Please enter valid start day!', 'danger')
        return False
    if not date_event_stop_form or not test_pattern(pattern_date, date_event_stop_form):
        flash(f'Please enter valid stop day!', 'danger')
        return False
    if date_event_notify_form and not test_pattern(pattern_date, date_event_notify_form):
        flash(f'Please enter valid notify day!', 'danger')
        return False
    return True


@main_bp.route('/new_event', methods=['GET', 'POST'])
@cancel_click('main_bp.index')
@login_required
def new_event():
    """
    Add new event to db.
    """
    users_to_notify = User.query.filter_by(role_id=2).all()
    today = datetime.date.today().strftime("%Y-%m-%d")
    if request.method == "POST":
        # Form validation - sever-side
        if not event_validation(request):
            return redirect(url_for('main_bp.new_event'))
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
        # Assign user
        users_form = request.form.getlist('notified_user')
        for user_id in users_form:
            user = User.query.get(user_id)
            user.events_notified.append(event)
            db.session.add(user)
        db.session.commit()
        flash('New event has been added!', 'success')
        current_app.logger_general.info(f'New event with id={event.id} has been added by "{current_user}"')
        return redirect(url_for('main_bp.index'))
    return render_template('new_event.html', title='New event', users=users_to_notify, today=today)


@main_bp.route('/event/<int:event_id>', methods=['GET', 'POST'])
@cancel_click()
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
        current_app.logger_general.info(f'Event with id={event.id} has been changed by "{current_user}"')
        current_app.logger_general.info(f'Event with id={event.id} has been deactivated by "{current_user}"')
        if 'prev_endpoint' in session:
            return redirect(session['prev_endpoint'])
        return redirect(url_for('main_bp.events_list'))
    return render_template('event.html', event=event, title='Edit event', users=users_to_notify, today=today)


@main_bp.route('/dea_event/<int:event_id>')
@login_required
def deactive_event(event_id):
    """
    Remove event from 'events_list' - only deactivate event (not delete).
    """
    event = Event.query.filter_by(id=event_id).first()
    if (current_user.id != event.author.id) and (not current_user.is_admin()):
        flash("Sorry! You can't delete someone's event!", 'danger')
        if session.get('prev_endpoint'):
            return redirect(session['prev_endpoint'])
        else:
            return redirect(url_for('main_bp.events_list'))
    event.is_active = False
    db.session.commit()
    flash(f'Event with title "{event.title}" has been deleted!', 'success')
    # Custom small delay when deactivating search results (for elasticsearch better performance)
    if 'search' in session.get('prev_endpoint'):
        time.sleep(1)
    # Redirect to previous URL
    if session.get('prev_endpoint_dea'):
        return redirect(session.get('prev_endpoint_dea'))
    elif session.get('prev_endpoint'):
        return redirect(session['prev_endpoint'])
    return redirect(url_for('main_bp.events_list'))


@main_bp.route('/events_list/search')
def search():
    """
    Search engine for main blueprint
    """
    if not current_app.elasticsearch or not current_app.elasticsearch.ping():
        flash(f'Sorry! No connection with search engine!', 'danger')
        return redirect(session.get('prev_endpoint'))
    today = datetime.datetime.today()
    today_only_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
    # Fetch all current event's authors from db.
    event_authors = events_authors_func(today, today_only_day)[0]
    page = request.args.get('page', 1, type=int)
    events_per_page = 3
    # Return only 'is_active' events using elasticsearch query filter
    filter_data = {'is_active': True}
    try:
        events, total = Event.search(request.args.get('q'), page, events_per_page, filter_data)
    except (elasticsearch.exceptions.RequestError, TypeError):
        abort(404)
    next_url = url_for('main_bp.search', q=request.args.get('q'), page=page + 1) \
        if total > page * events_per_page else None
    prev_url = url_for('main_bp.search', q=request.args.get('q'), page=page - 1) \
        if page > 1 else None
    # Pagination for search results
    page_last = int(total / events_per_page) + 1 if (total / events_per_page % 1) != 0 else int(total / events_per_page)
    pagination = {
        'page_first': 1,
        'page_current': page,
        'page_last': page_last,
        'page_prev': page - 1 if page > 1 else None,
        'page_next': page + 1 if total > page * events_per_page else None,
        'events_per_page': events_per_page,
    }
    # Remember additional URL in session, if there is only one event on page - for event deactivation feature
    events_on_current_page = events.count()
    if session.get('prev_endpoint_dea'):
        del session['prev_endpoint_dea']
    if events_on_current_page == 1 and not page == 1:
        session['prev_endpoint_dea'] = url_for('main_bp.search',
                                               q=request.args.get('q'),
                                               page=page - 1)
    # Remember current url in session (for back-redirect)
    if not request.args.get('page'):
        session['prev_endpoint'] = url_for('main_bp.search',
                                           q=request.args.get('q'))
    else:
        session['prev_endpoint'] = url_for('main_bp.search',
                                           q=request.args.get('q'),
                                           page=page)
    return render_template('search.html',
                           title='Search',
                           events=events,
                           total=total,
                           next_url=next_url,
                           prev_url=prev_url,
                           today=today,
                           today_only_day=today_only_day,
                           event_authors=event_authors,
                           **pagination)


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



