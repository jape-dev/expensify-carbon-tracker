from flask import (
    Blueprint,
    current_app,
    redirect,
    request,
    flash,
    url_for,
    render_template)
from flask_login import (
    login_required,
    login_user,
    current_user)

from canopact.blueprints.company.models import Company
from canopact.blueprints.user.models import User
from canopact.blueprints.company.forms import InviteForm
from canopact.blueprints.user.forms import SignupForm
from canopact.blueprints.admin.forms import SearchForm, BulkDeleteForm
from canopact.blueprints.user.decorators import (anonymous_required,
                                                 role_required)
from sqlalchemy import text
# from canopact.blueprints.billing.decorators import subscription_required
from canopact.blueprints.billing.models.subscription import Subscription
import itsdangerous
from itsdangerous import URLSafeTimedSerializer
from lib.util_datetime import tzware_datetime

company = Blueprint('company', __name__, template_folder='templates',
                    url_prefix='/company')


@company.route('/invite', methods=['GET', 'POST'])
@login_required
def invite():
    """Route to invite a new user to the company"""

    form = InviteForm()

    if form.validate_on_submit():
        email = request.form.get('email')
        Company.initialize_invite(email, current_user.email)

        flash('An email has been sent to {0}.'.format(email), 'success')
        return redirect(url_for('user.settings'))

    return render_template('invite.html', form=form)


@company.route('/invite/<token>/<email>', methods=['GET', 'POST'])
@anonymous_required()
def invite_signup(token, email):
    """Route for invited user to sign up for an account.

    Args:
        token (str): unique token from the users invite email.
        email (str): email of the invited user.

    Returns:
        flask.render_template: if user comes from email url.
        flask.redirect: if user submits the form.

    """
    try:
        invite_serializer = URLSafeTimedSerializer(
            current_app.config['SECRET_KEY'])
        invite = invite_serializer.loads(token, max_age=86400)
    except itsdangerous.exc.BadTimeSignature as e:
        print(e)
        flash('The invite link is invalid or has expired.', 'error')
        return redirect(url_for('user.login'))

    company = Company.query.get(int(invite[1]))

    form = SignupForm()
    form.email.data = email
    form.name.data = company.name
    form.industry.data = company.industry
    form.employees.data = company.employees
    form.country.data = company.country
    form.invited = True

    if form.validate_on_submit():
        # Increment the per user billing quantity.
        if company.payment_id:
            s = Subscription()
            s.add(company)

        # Create the new user.
        u = User()
        form.populate_obj(u)
        u.password = User.encrypt_password(request.form.get('password'))
        u.role = 'member'
        u.company_id = company.id
        u.email_confirmed = True
        u.email_confirmed_on = tzware_datetime()
        u.save()

        if login_user(u):
            flash('Thank you for registering. Welcome to Canopact', 'success')
            return redirect(url_for('user.settings'))

    return render_template('user/signup.html', form=form, token=token,
                           email=email)


@company.route('/portal', methods=['GET'])
@login_required
@role_required('company_admin')
# @subscription_required
def portal():
    """
    Route for company_admin's to access their company portal.

    Returns:
        Flask.render_template: company portal page.

    """
    company = Company.query.get(current_user.company_id)
    days_left_on_trial = company.days_left_on_trial()

    return render_template('company/portal.html', company=company,
                           days_left_on_trial=days_left_on_trial)


# Users -----------------------------------------------------------------------
@company.route('/users', defaults={'page': 1})
@company.route('/users/page/<int:page>')
def users(page):
    search_form = SearchForm()
    bulk_form = BulkDeleteForm()

    sort_by = User.sort_by(request.args.get('sort', 'created_on'),
                           request.args.get('direction', 'desc'))
    order_values = '{0} {1}'.format(sort_by[0], sort_by[1])

    paginated_users = User.query \
        .filter(User.search(request.args.get('q', ''))) \
        .filter(User.company_id == current_user.company_id) \
        .order_by(User.role.asc(), User.payment_id, text(order_values)) \
        .paginate(page, 50, True)

    return render_template('company/user/index.html',
                           form=search_form, bulk_form=bulk_form,
                           users=paginated_users)
