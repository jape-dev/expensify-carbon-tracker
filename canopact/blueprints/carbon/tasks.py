"""Celery Beat Task for updating Report, Expense, Route and Carbon.

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
from canopact.blueprints.carbon.models.expense import Carbon
from canopact.blueprints.carbon.models.expense import Expense
from canopact.blueprints.carbon.models.report import Report
from canopact.blueprints.carbon.models.route import Route, Distance
from canopact.blueprints.user.models import User
from canopact.extensions import db
import pandas as pd


celery = create_celery_app()


@celery.task(bind=True)
def fetch_reports(self):
    """Fetch expense reports from Expensify Integration Server.

    Data on expenses is also parsed from these reports.

    TODO:
        * add handling for if a user does not have their expensify creds.
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

    print('Fetch reports complete.')


@celery.task(bind=True)
def calculate_carbon(self):
    """Calculates carbon for new travel expense reports.

    Saves records to `routes` and `carbon` tables.

    TODO:
        * Use distance for routes that already exist instead of
          calculating distance again.
    """
    # Get new expense reports that do not have carbon calculates.
    new = Expense.get_new_expenses()

    # Format and create additional route columns required.
    new = Route.create_routes(new)

    # If no new routes from expenses or ammended routes.
    if new is None:
        return None

    # Calculate distances against routes.
    distances = Distance.calculate_distance(new)

    # Convert NaNs to nulls to be compaitible to SQL db.
    distances = distances.where(pd.notnull(distances), None)

    # Reduce route cols down to cols of interest and convert to a dictionary.
    route_df = distances[['expense_id', 'expense_category', 'route_category',
                          'origin', 'destination', 'invalid', 'distance']]

    route_dict = route_df.to_dict('records')

    # Reduce carbon cols down to cols of interest and convert to a dictionary.
    carbon_df = distances[['expense_id', 'origin', 'destination',
                           'expense_category', 'distance']]
    carbon_df = carbon_df[carbon_df['distance'].notnull()]
    carbon_dict = carbon_df.to_dict('records')

    # Save route records to db.
    for d in route_dict:
        r = Route(**d)
        r.update_and_save(Route, expense_id=r.expense_id)

    # Convert distances to carbon and save records to db.
    for d in carbon_dict:
        c = Carbon.emissions(**d)
        c.update_and_save(Carbon, expense_id=d['expense_id'])

    print('Calculate Carbon complete.')
