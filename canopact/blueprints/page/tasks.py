from lib.flask_mailplus import send_template_message
from canopact.app import create_celery_app

celery = create_celery_app()


@celery.task()
def deliver_register_email(email):
    """
    Send a contact e-mail.

    Calls:
        lib.flask_mailplus.send_template_message()

    Args:
        email (str): e-mail address of the
        landing page visitor.

    """
    ctx = {'email': email}

    send_template_message(subject='Canopact Landing Page Sign Up',
                          recipients=['info@canopact.com'],
                          template='mail/index', ctx=ctx)
