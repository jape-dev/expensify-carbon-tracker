from functools import wraps

import stripe
from flask import redirect, url_for, flash
from flask_login import current_user


def subscription_required(f):
    """
    Ensure a user is subscribed, if not redirect them to the pricing table.

    :return: Function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from canopact.blueprints.company.models import Company
        company = Company.query.get(current_user.company_id)
        if not company.trial_active:
            flash('Your trial has now finished. Please contact info@canopact.com for next steps.', 'error')
            return redirect(url_for('user.settings'))

        return f(*args, **kwargs)

    return decorated_function


def handle_stripe_exceptions(f):
    """
    Handle Stripe exceptions so they do not throw 500s.

    :param f:
    :type f: Function
    :return: Function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except stripe.error.CardError:
            flash('Sorry, your card was declined. Try again perhaps?', 'error')
            return redirect(url_for('user.settings'))
        except stripe.error.InvalidRequestError as e:
            flash(e, 'error')
            return redirect(url_for('user.settings'))
        except stripe.error.AuthenticationError:
            flash('Authentication with our payment gateway failed.', 'error')
            return redirect(url_for('user.settings'))
        except stripe.error.APIConnectionError:
            flash(
                'Our payment gateway is experiencing connectivity issues'
                ', please try again.', 'error')
            return redirect(url_for('user.settings'))
        except stripe.error.StripeError:
            flash(
                'Our payment gateway is having issues, please try again.',
                'error')
            return redirect(url_for('user.settings'))

    return decorated_function
