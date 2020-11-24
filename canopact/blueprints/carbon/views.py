"""Views for Canopact carbon dashboard."""

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


carbon = Blueprint('carbon', __name__, template_folder='templates')

# Dashboard -------------------------------------------------------------------
@email_confirm_required()
@carbon.route('/carbon', methods=['GET', 'POST'])
def dashboard():
    """Renders template for the carbon dashboard"""
    return render_template('dashboard.html',
                           report_id=5)


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
