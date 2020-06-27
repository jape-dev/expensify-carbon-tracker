from lib.flask_mailplus import send_template_message
from canopact.app import create_celery_app
from canopact.blueprints.user.models import User

celery = create_celery_app()


@celery.task()
def deliver_password_reset_email(user_id, reset_token):
    """
    Send a reset password e-mail to a user.

    :param user_id: The user id
    :type user_id: int
    :param reset_token: The reset token
    :type reset_token: str
    :return: None if a user was not found
    """
    user = User.query.get(user_id)

    if user is None:
        return

    ctx = {'user': user, 'reset_token': reset_token}

    send_template_message(subject='Password reset from Canopact',
                          recipients=[user.email],
                          template='user/mail/password_reset', ctx=ctx)

    return None


@celery.task()
def deliver_confirmation_email(user_id, confirm_url):
    """
    Sends an account confirmation email to the user.

    Args:
        user_id (int): the user id.
        confirm_url (str): confirmation url for user to click on.

    Returns:
        None if no user found.
    """
    user = User.query.get(user_id)

    if user is None:
        return

    ctx = {'user': user, 'confirm_url': confirm_url}

    send_template_message(subject='Please confirm your Canopact account',
                          recipients=[user.email],
                          template='user/mail/email_confirmation', ctx=ctx)

    return None
