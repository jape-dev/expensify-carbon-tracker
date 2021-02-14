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
        .filter(Route.route_category != 'unit') \
        .filter((Route.origin.is_(None) | Route.destination.is_(None)) |
                (Route.invalid == 1)) \
        .filter(Route.search(request.args.get('q', ''))) \
        .order_by(text(order_values)) \
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

            # Update and save the Route model.
            if all(v is not None for v in [origin, destination]):
                r.origin = origin
                r.destination = destination
                r.invalid = 0  # Change the invalid flag.
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
                           routes=routes, total=total, key=key)
