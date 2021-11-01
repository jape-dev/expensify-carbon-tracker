"""Views for Canopact carbon dashboard.

"""


import datetime
import json

from canopact.blueprints.carbon.models.carbon import Carbon
from canopact.blueprints.carbon.models.expense import Expense
from canopact.blueprints.carbon.models.report import Report
from canopact.blueprints.carbon.models.route import Route
from canopact.blueprints.carbon.forms import (
    SearchForm,
    RouteForm,
    JourneysForm,
    DateForm
)
from canopact.blueprints.billing.decorators import (
    subscription_required
)
from canopact.blueprints.user.decorators import (
    email_confirm_required,
    expensify_required
)
from canopact.extensions import db, cache
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
    request,
)
from flask_login import current_user, login_required
from sqlalchemy import text

carbon = Blueprint('carbon', __name__, template_folder='templates')


# Dashboard -------------------------------------------------------------------
@cache.cached(timeout=300, key_prefix="date_input")
def get_date_input():
    """Get value from date input form and convert to date.

    Caches date input so that it persists across different levels of
        aggregation.

    Returns:
        date (datetime.datetime): date from input form.

    """
    date = request.form.get('date')
    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()

    return date


@carbon.route('/carbon/dashboard/<agg>', methods=['GET', 'POST'])
# @expensify_required()
@subscription_required
@email_confirm_required()
@login_required
def dashboard(agg):
    """Renders template for the carbon dashboard

    Args:
        agg (str): level of aggregation for the dashboards

    """
    form = DateForm()

    # Date input.
    if form.validate_on_submit():
        cache.clear()
        date = get_date_input()
    else:
        try:
            date = get_date_input()
        except BaseException:
            date = datetime.date.today()

    # Update data in form.
    form.date.data = date

    # KPI cards.
    emissions, prev_emissions, emissions_change = \
        Carbon.emissions_metrics(current_user, agg=agg, date=date)
    per_journeys, prev_per_journeys, per_journeys_change = \
        Carbon.per_journeys_metrics(current_user, agg=agg, date=date)
    cost, prev_cost, cost_change = \
        Carbon.cost_metrics(current_user, agg=agg, date=date)
    cost_per_journey, prev_cost_per_journey, cost_per_journey_change = \
        Carbon.cost_per_journey_metrics(current_user, agg=agg, date=date)

    # Charts.
    journeys = Carbon.group_and_count_journeys_monthly(current_user, agg=agg,
                                                       date=date)
    monthly_carbon = Carbon.group_and_sum_emissions_monthly(current_user,
                                                            agg=agg,
                                                            prev_months=8,
                                                            date=date)
    line = Carbon.emissions_metrics_monthly(current_user, agg=agg,
                                            prev_months=8,
                                            emissions=monthly_carbon,
                                            date=date)

    # Line chart filters.
    emissions_line = line["datasets"]["emissions"]
    per_journey_line = line["datasets"]["per_journey"]
    per_km_line = line["datasets"]["per_km"]

    # Tables.
    transports = Carbon.group_and_count_transport(current_user, agg=agg,
                                                  as_list=True, date=date)
    routes = Carbon.group_and_count_routes(current_user, agg=agg, as_list=True,
                                           date=date)

    return render_template('dashboard/index.html', emissions=emissions,
                           emissions_change=emissions_change,
                           emissions_per_journeys=per_journeys,
                           per_journeys_change=per_journeys_change,
                           cost=cost,
                           cost_change=cost_change,
                           cost_per_journey=cost_per_journey,
                           cost_per_journey_change=cost_per_journey_change,
                           journeys=json.dumps(journeys),
                           monthly_carbon=json.dumps(monthly_carbon),
                           emissions_line=json.dumps(emissions_line),
                           per_journey_line=json.dumps(per_journey_line),
                           per_km_line=json.dumps(per_km_line),
                           routes=routes, transports=transports,
                           form=form)


# Routes Cleaner --------------------------------------------------------------
def get_routes():
    """Fetches routes that do not have a valid origin/destination.

    Orders routes according to sorting selected on the router cleaner table.

    Returns:
        routes (sqlachemy.Query): routes which require origin/destination
            values to be updated.

    """

    sort_by = Route.sort_by(request.args.get('sort', 'expense_created_date'),
                            request.args.get('direction', 'desc'))
    order_values = 'routes.{0} {1}'.format(sort_by[0], sort_by[1])

    routes = db.session.query(Route.id,
                              Route.created_on,
                              Route.expense_id,
                              Route.expense_category,
                              Report.report_name,
                              Expense.expense_merchant,
                              Expense.expense_comment,
                              Expense.expense_created_date) \
        .join(Expense, Route.expense_id == Expense.expense_id) \
        .join(Report, Expense.report_id == Report.report_id) \
        .filter(Expense.user_id == current_user.id) \
        .filter(Route.route_category != 'unit') \
        .filter((Route.origin.is_(None) | Route.destination.is_(None)) |
                (Route.invalid == 1)) \
        .filter(Route.search(request.args.get('q', ''))) \
        .order_by(text(order_values)) \
        .distinct()

    return routes


@carbon.route('/carbon/cleaner')
# @expensify_required()
@subscription_required
@email_confirm_required()
@login_required
def cleaner():
    """Retrieves all expenses with an invalid and renders cleaner template."""

    search_form = SearchForm()
    routes = get_routes()

    return render_template('cleaner/cleaner.html', form=search_form,
                           routes=routes)


@carbon.route('/carbon/cleaner/edit', methods=['GET', 'POST'])
# @expensify_required()
@email_confirm_required()
@login_required
def routes_edit():
    """Opens editor mode to let user enter in valid origin and destination.

    """
    routes = get_routes()
    total = int(routes.count())  # total number of invalid routes.

    journeys_form = JourneysForm()

    # Key for Google Autocomplete API.
    key = current_app.config['DISTANCE_KEY']

    # Iterate over each route submitted on the cleaner.
    if journeys_form.validate_on_submit():
        for i, entry in enumerate(journeys_form.journeys.entries):
            # Get the route id in order to instantiate a Route object.
            id = journeys_form.ids[i]
            r = Route.query.get(id)

            # Parse the fields from the FieldList.
            if entry.data['origin'] == '':
                origin = None
            else:
                origin = entry.data['origin']

            if entry.data['destination'] == '':
                destination = None
            else:
                destination = entry.data['destination']

            if entry.data['return_type']:
                return_type = 'return'
            else:
                return_type = None

            # Update and save the Route model.
            if all(v is not None for v in [origin, destination]):
                r.origin = origin
                r.destination = destination
                r.return_type = return_type
                r.invalid = 0  # Change the invalid flag.
                r.update_and_save(Route, id=id)

        # Clear journeys form.
        while len(journeys_form.journeys.entries) > 0:
            journeys_form.journeys.pop_entry()
        while len(journeys_form.ids) > 0:
            journeys_form.ids.pop()

        flash('Routes has been saved successfully.', 'success')
        return redirect(url_for('carbon.cleaner'))
    else:
        # Clear journeys form.
        while len(journeys_form.journeys.entries) > 0:
            journeys_form.journeys.pop_entry()
        while len(journeys_form.ids) > 0:
            journeys_form.ids.pop()

        for route in routes:
            route_form = RouteForm()
            route_form.origin = None
            route_form.destination = None
            route_form.return_type = None
            journeys_form.ids.append(route.id)
            journeys_form.journeys.append_entry(route_form)

    return render_template('cleaner/edit.html', form=journeys_form,
                           routes=routes, total=total, key=key)
