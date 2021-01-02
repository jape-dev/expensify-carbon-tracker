"""Views for Canopact carbon dashboard.

"""

import json

from canopact.blueprints.carbon.models.carbon import Carbon
from canopact.blueprints.carbon.models.expense import Expense
from canopact.blueprints.carbon.models.report import Report
from canopact.blueprints.carbon.models.route import Route
from canopact.blueprints.carbon.forms import (
    SearchForm,
    RouteForm,
    JourneysForm
)
from canopact.blueprints.user.decorators import email_confirm_required
from canopact.extensions import db
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    url_for
)
from flask_login import current_user, login_required


carbon = Blueprint('carbon', __name__, template_folder='templates')

# Dashboard -------------------------------------------------------------------
@login_required
@email_confirm_required
@carbon.route('/carbon/dashboard/<agg>', methods=['GET', 'POST'])
def dashboard(agg):
    """Renders template for the carbon dashboard

    Args:
        agg (str): level of aggregation for the dashboards

    """
    emissions = Carbon.group_and_sum_emissions(current_user, agg=agg)
    journeys = Carbon.group_and_sum_journeys(current_user, agg=agg)
    monthly_carbon = Carbon.group_and_sum_emissions_monthly(current_user,
                                                            agg=agg,
                                                            prev_months=8)
    transports = Carbon.group_and_count_transport(current_user, agg=agg,
                                                  as_list=True)
    routes = Carbon.group_and_count_routes(current_user, agg=agg, as_list=True)

    return render_template('dashboard/index.html', emissions=emissions,
                           journeys=json.dumps(journeys),
                           monthly_carbon=json.dumps(monthly_carbon),
                           routes=routes, transports=transports)


# Routes Cleaner --------------------------------------------------------------
def get_routes():
    """Fetches expense records that do not have a valid origin/destination."""
    routes = db.session.query(Route.id,
                              Route.expense_id,
                              Report.report_name,
                              Expense.expense_merchant,
                              Expense.expense_comment,
                              Expense.expense_created_date) \
        .join(Expense, Route.expense_id == Expense.expense_id) \
        .join(Report, Expense.report_id == Report.report_id) \
        .filter(Route.route_category != 'unit') \
        .filter((Route.origin.is_(None) & Route.destination.is_(None)) |
                (Route.invalid == 1)) \
        .distinct()

    return routes


@email_confirm_required()
@carbon.route('/carbon/cleaner')
def cleaner():
    """Retrieves all expenses with an invalid and renders cleaner template."""
    search_form = SearchForm()
    routes = get_routes()

    return render_template('cleaner/cleaner.html', form=search_form,
                           routes=routes)


@carbon.route('/carbon/cleaner/edit', methods=['GET', 'POST'])
def routes_edit():
    """Opens editor mode to let user enter in valid origin and destination.

    """
    routes = get_routes()
    journeys_form = JourneysForm()

    if journeys_form.validate_on_submit():
        for i, entry in enumerate(journeys_form.journeys.entries):
            id = journeys_form.ids[i]
            r = Route.query.get(id)

            if entry.data['origin'] == '':
                origin = None
            else:
                origin = entry.data['origin']

            if entry.data['destination'] == '':
                destination = None
            else:
                destination = entry.data['destination']

            r.origin = origin
            r.destination = destination
            r.update_and_save(Route, id=id)

        flash('Routes has been saved successfully.', 'success')
        return redirect(url_for('carbon.cleaner'))
    else:
        for route in routes:
            route_form = RouteForm()
            route_form.origin = None
            route_form.destination = None
            journeys_form.ids.append(route.id)
            journeys_form.journeys.append_entry(route_form)

    return render_template('cleaner/edit.html', form=journeys_form,
                           routes=routes)
