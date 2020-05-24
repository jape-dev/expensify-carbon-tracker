from canopact.app import create_celery_app
from canopact.blueprints.user.models import User
from vendors import expensify


celery = create_celery_app()


@celery.task(bind=True)
def fetch_reports(self, user_id):
    """
    Fetch reports from Expensify Integration Server.

    Returns:
        reports (list): expensify reports in JSON format.
    """
    user = User.query.get(user_id)

    # Get user Expensify API credentials.
    partnerUserID = user.partnerUserID
    partnerUserSecret = user.partnerUserSecret

    # Get all reports from Expensify Integration Server.
    reports = expensify.main(partnerUserID, partnerUserSecret)

    return reports
