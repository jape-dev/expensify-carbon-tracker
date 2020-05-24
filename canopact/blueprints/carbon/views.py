from canopact.blueprints.carbon.models import Report
from canopact.blueprints.carbon.models import Expense
from flask import (
    Blueprint,
    render_template)
from flask_login import current_user


carbon = Blueprint('carbon', __name__, template_folder='templates')


@carbon.route('/carbon', methods=['GET', 'POST'])
def update_reports():
    """Updates user's reports information."""
    # Prevent circular import.
    from canopact.blueprints.carbon.tasks import fetch_reports

    if current_user.is_authenticated:
        user_id = current_user.id
        # reports = Report(user_id=user_id)

        # Fetch reports frome expensify integration server.
        result = fetch_reports.delay(user_id)
        report_list = result.get()

        # Parse reports
        reports = Report.parse_report_from_list(report_list, 1,
                                                user_id)
        report = Report(**reports)
        report.save_and_update_report()

        all_expenses = Expense.parse_expenses_from_list(report_list, 1,
                                                        user_id)
        first_expense = Expense.parse_expense_from_report(all_expenses, 0)

        expense = Expense(**first_expense)
        expense.save_and_update_expense()

    return render_template('carbon/carbon_dashboard.html',
                           report_count=5)
