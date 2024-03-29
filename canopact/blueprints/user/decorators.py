from functools import wraps

from flask import flash, redirect
from flask_login import current_user


def anonymous_required(url='/settings'):
    """
    Redirect a user to a specified location if they are already signed in.

    :param url: URL to be redirected to if invalid
    :type url: str
    :return: Function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.is_authenticated:
                return redirect(url)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def role_required(*roles):
    """
    Does a user have permission to view this page?

    :param *roles: 1 or more allowed roles
    :return: Function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.role not in roles:
                flash('You do not have permission to do that.', 'error')
                return redirect('/')

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def email_confirm_required(url='/'):
    """
    Restrict users from accessing page if they have not confirmed their email.

    Return:
        function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.email_confirmed:
                flash('You must confirm your email address before viewing this'
                      ' page.', 'error')
                return redirect(url)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def expensify_required(url='/settings/expensify_login'):
    """
    Restrict users from accessing page if they have not submitted their
    expensify credentials.

    Args:
        url (str): URL to be redirected to if expensify credentials
            not submitted.

    Return:
        function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.expensify_id:
                flash('Please authenticate your Expensify API to view this '
                      'page or check that your Expensify credentials are up to '
                      'date.', 'success')
                return redirect(url)

            return f(*args, **kwargs)

        return decorated_function

    return decorator
