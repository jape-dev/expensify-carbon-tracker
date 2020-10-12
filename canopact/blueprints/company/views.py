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
from canopact.blueprints.user.decorators import anonymous_required
import itsdangerous
from itsdangerous import URLSafeTimedSerializer
from lib.util_datetime import tzware_datetime

company = Blueprint('company', __name__, template_folder='templates')


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
    form.company.data = company.name
    form.invited = True

    if form.validate_on_submit():
        u = User()
        c = Company()

        form.populate_obj(c)
        c.save()

        form.populate_obj(u)
        u.password = User.encrypt_password(request.form.get('password'))
        u.company_id = c.id
        u.email_confirmed = True
        u.email_confirmed_on = tzware_datetime()
        u.save()

        if login_user(u):
            flash('Thanks for registering!')
            return redirect(url_for('user.settings'))

    return render_template('user/signup.html', form=form, token=token,
                           email=email)
