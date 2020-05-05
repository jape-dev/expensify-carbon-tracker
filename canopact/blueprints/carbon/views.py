from canopact.blueprints.carbon.models import Report
from flask import (
    Blueprint,
    render_template)
from flask_login import current_user


carbon = Blueprint('carbon', __name__, template_folder='templates')


@carbon.route('/carbon', methods=['GET', 'POST'])
def update_reports():
    """Updates user's reports information."""
    # prevent circular import
    from canopact.blueprints.carbon.tasks import fetch_reports

    if current_user.is_authenticated:
        user_id = current_user.id
        reports = Report(user_id=user_id)

        # Fetch reports frome expensify integration server.
        result = fetch_reports.delay(user_id)
        expensify_reports = result.get()
        report_count = len(expensify_reports)

        # Save user's report data into the reports table.
        reports.report_count = report_count
        reports.save_and_update_report()

    return render_template('carbon/carbon_dashboard.html',
                           report_count=reports.report_count)
