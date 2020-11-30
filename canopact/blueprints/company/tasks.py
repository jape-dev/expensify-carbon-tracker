from lib.flask_mailplus import send_template_message
from canopact.app import create_celery_app
from canopact.blueprints.company.models import Company

celery = create_celery_app()


@celery.task()
def deliver_invite_email(to_email, from_email, invite_url):
    """
    Sends an account confirmation email to the user.

    Args:
        to_email (str): email of new user who is being invited.
        from_email (str): the uexisting ser email who made the invite.
        invite_url (str): url to take new user to the sign up form.

    Returns:
        None

    """
    ctx = {'from_email': from_email, 'invite_url': invite_url}

    send_template_message(subject='You have been invited to join Canopact',
                          recipients=[to_email],
                          template='company/mail/email_invite',
                          ctx=ctx)

    return None


@celery.task()
def expire_free_trials():
    """
    Inactivate free trials once they have reached their expiry date.

    Returns:
        Result of updating the records.

    """
    return Company.expire_free_trials()
