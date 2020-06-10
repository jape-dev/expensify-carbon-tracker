"""Celery Beat Task for updating Report and Expense.

Fetches data from the Expensify Integration Server via Expensify's Public API:
https://integrations.expensify.com/Integration-Server/doc/

Notes:
    Example Celery Beat config:
        CELERYBEAT_SCHEDULE = {
        'fetch-expensify-reports': {
            'task': 'canopact.blueprints.carbon.tasks.fetch_reports',
            'schedule': 10
            }
        }
"""
from canopact.app import create_celery_app
from canopact.blueprints.carbon.models import Expense
from canopact.blueprints.carbon.models import Report
from canopact.blueprints.user.models import User
from canopact.extensions import db


celery = create_celery_app()


@celery.task(bind=True)
def fetch_reports(self):
    """Fetch expense reports from Expensify Integration Server.

    Data on expenses is also parsed from these reports.

    TODO:
        * Ammend user_ids definition to only include active customers.
        * Replace nested for loops with parralelised workers.
    """
    # Get a list of the currently active user ids.
    user_ids = [u[0] for u in db.session.query(User.id).distinct()]
    # Get a list of all Expensify reports currently belonging to these users.
    user_reports = Report.fetch_expensify_reports(User, user_ids)

    # Loop over each user's reports.
    for uid, report_list in user_reports.items():
        # Loop through each of the reports belonging to the user.
        for i in range(len(report_list)):
            # Get the required fields and save into a dict.
            r_dict = Report.parse_report_from_list(report_list, i, uid)
            # Instantiate the report using the dict.
            r = Report(**r_dict)
            r.update_and_save(Report, report_id=r.report_id)

            # Retrieve report expenses by using the same positional index.
            r_expenses = Expense.parse_expenses_from_list(report_list, i, uid)
            # Iterate over the expenses in each report.
            for j in range(len(r_expenses['expense_id'])):
                # Get the required fields and save into a dict.
                e_dict = Expense.parse_expense_from_report(r_expenses, j)
                # Instantiate the expense using the dict.
                e = Expense(**e_dict)
                # Save expense into db table.
                e.update_and_save(Expense, expense_id=e.expense_id)
