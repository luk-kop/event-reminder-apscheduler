from flask import request, abort, redirect, url_for, current_app, flash, session
from functools import wraps
from flask_login import current_user


def admin_required(view):
    """
    Decorator check if current user has admin privileges.
    """
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def cancel_click(prev_url=None):
    """
    Decorator check if cancel button has been pressed and if True redirect to selected URL or previous URL.
    """
    def inner_decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if request.method == "POST" and request.form.get('cancel-btn') == 'Cancel':
                if prev_url:
                    return redirect(url_for(prev_url))
                elif session.get('prev_endpoint'):
                    return redirect(session.get('prev_endpoint'))
            return view(*args, **kwargs)
        return wrapper
    return inner_decorator


def login_required(view):
    """
    Decorator ensure that the current user is logged in and authenticated before calling the actual view.
    Moreover, if the current_user is obliged to change the password, it redirects him to the password change endpoint.
    """
    @wraps(view)
    def decorated_view(*args, **kwargs):
        if request.method in ['OPTIONS']:
            return view(*args, **kwargs)
        elif current_app.config.get('LOGIN_DISABLED'):
            return view(*args, **kwargs)
        elif not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        elif current_user.pass_change_req and view.__name__ != 'change_pass':
            flash('Please change your password', 'success')
            return redirect(url_for('auth_bp.change_pass'))
        return view(*args, **kwargs)
    return decorated_view