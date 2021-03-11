from flask import (
    current_app,
    Blueprint,
    redirect,
    request,
    flash,
    url_for,
    render_template)
from flask_login import (
    login_required,
    login_user,
    current_user,
    logout_user)

from lib.util_datetime import tzware_datetime
from lib.safe_next_url import safe_next_url
from canopact.blueprints.user.decorators import (
    anonymous_required, email_confirm_required)
from canopact.blueprints.company.models import Company
from canopact.blueprints.user.models import User
from canopact.blueprints.user.forms import (
    LoginForm,
    BeginPasswordResetForm,
    PasswordResetForm,
    SignupForm,
    UpdateCredentialsForm,
    ExpensifyAPICredentialsForm,
    UpdateLocaleForm,
    ResendEmailForm)
import itsdangerous
from itsdangerous import URLSafeTimedSerializer
from vendors.salesforce import get_redirect_url, get_tokens


user = Blueprint('user', __name__, template_folder='templates')


@user.route('/login', methods=['GET', 'POST'])
@anonymous_required()
def login():
    form = LoginForm(next=request.args.get('next'))

    if form.validate_on_submit():
        u = User.find_by_identity(request.form.get('identity'))

        if u and u.authenticated(password=request.form.get('password')):
            # As you can see remember me is always enabled, this was a design
            # decision I made because more often than not users want this
            # enabled. This allows for a less complicated login form.
            #
            # If however you want them to be able to select whether or not they
            # should remain logged in then perform the following 3 steps:
            # 1) Replace 'True' below with: request.form.get('remember', False)
            # 2) Uncomment the 'remember' field in user/forms.py#LoginForm
            # 3) Add a checkbox to the login form with the id/name 'remember'
            if login_user(u, remember=True) and u.is_active():
                u.update_activity_tracking(request.remote_addr)

                # Handle optionally redirecting to the next URL safely.
                next_url = request.form.get('next')
                if next_url:
                    return redirect(safe_next_url(next_url))

                return redirect(url_for('user.settings'))
            else:
                flash('This account has been disabled.', 'error')
        else:
            flash('Identity or password is incorrect.', 'error')

    return render_template('user/login.html', form=form)


@user.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('user.login'))


@user.route('/account/begin_password_reset', methods=['GET', 'POST'])
@anonymous_required()
def begin_password_reset():
    form = BeginPasswordResetForm()

    if form.validate_on_submit():
        u = User.initialize_password_reset(request.form.get('identity'))

        flash('An email has been sent to {0}.'.format(u.email), 'success')
        return redirect(url_for('user.login'))

    return render_template('user/begin_password_reset.html', form=form)


@user.route('/account/password_reset', methods=['GET', 'POST'])
@anonymous_required()
def password_reset():
    form = PasswordResetForm(reset_token=request.args.get('reset_token'))

    if form.validate_on_submit():
        u = User.deserialize_token(request.form.get('reset_token'))

        if u is None:
            flash('Your reset token has expired or was tampered with.',
                  'error')
            return redirect(url_for('user.begin_password_reset'))

        form.populate_obj(u)
        u.password = User.encrypt_password(request.form.get('password'))
        u.save()

        if login_user(u):
            flash('Your password has been reset.', 'success')
            return redirect(url_for('user.settings'))

    return render_template('user/password_reset.html', form=form)


@user.route('/signup', methods=['GET', 'POST'])
@anonymous_required()
def signup():
    form = SignupForm()

    if form.validate_on_submit():
        u = User()
        c = Company()

        form.populate_obj(c)
        c.save()

        form.populate_obj(u)
        u.password = User.encrypt_password(request.form.get('password'))
        u.company_id = c.id
        u.save()

        if login_user(u):
            User.initialize_email_confirmation(request.form.get('email'))
            flash('Thanks for registering!  Please check your email to '
                  ' confirm your email address.', 'success')
            return redirect(url_for('user.awaiting'))

    return render_template('user/signup.html', form=form)


@user.route('/awaiting', methods=['GET', 'POST'])
def awaiting():
    form = ResendEmailForm()
    if form.validate_on_submit():
        u = User.initialize_email_confirmation(request.form.get('identity'))
        flash('An email has been sent to {0}.'.format(u.email), 'success')
    return render_template('user/begin_email_confirmation.html', form=form)


@user.route('/confirm/<token>')
def confirm_email(token):
    try:
        confirm_serializer = URLSafeTimedSerializer(
            current_app.config['SECRET_KEY'])
        email = confirm_serializer.loads(token, max_age=3600)
    except itsdangerous.exc.BadTimeSignature as e:
        print(e)
        flash('The confirmation link is invalid or has expired.', 'error')
        return redirect(url_for('user.login'))

    user = User.query.filter_by(id=email[0]).first()

    if user.email_confirmed:
        flash('Account already confirmed. Please login.', 'info')
    else:
        user.email_confirmed = True
        user.email_confirmed_on = tzware_datetime()
        user.save()
        flash('Thank you for confirming your email address!', 'success')

    return redirect(url_for('user.settings'))


@user.route('/settings')
@login_required
@email_confirm_required()
def settings():

    company = Company.query.get(current_user.company_id)
    start = tzware_datetime()
    days_left_on_trial = company.days_left_on_trial(start=start)

    return render_template('user/settings.html', company=company,
                           days_left_on_trial=days_left_on_trial)


@user.route('/settings/update_credentials', methods=['GET', 'POST'])
@login_required
def update_credentials():
    form = UpdateCredentialsForm(current_user, uid=current_user.id)

    if form.validate_on_submit():
        new_password = request.form.get('password', '')
        current_user.email = request.form.get('email')

        if new_password:
            current_user.password = User.encrypt_password(new_password)

        current_user.save()

        flash('Your sign in settings have been updated.', 'success')
        return redirect(url_for('user.settings'))

    return render_template('user/update_credentials.html', form=form)


@user.route('/settings/salesforce_login', methods=['GET'])
@login_required
def salesforce_login():
    oauth_redirect = get_redirect_url()
    return redirect(oauth_redirect)


@user.route('/oauth2/callback', methods=['GET'])
@login_required
def salesforce_authorize():
    # Get the authorisation code from the url.
    code = request.args.get('code')
    # Retrive the tokens using the code.
    instance, access, refresh = get_tokens(code)
    # Save tokens to the user model.
    current_user.sf_instance_url = instance
    current_user.sf_access_token = access
    current_user.sf_refresh_token = refresh
    current_user.sf_token_activated_on = tzware_datetime()
    current_user.save()

    flash('Salesforce account successfully authenticated.', 'success')

    return redirect(url_for('user.settings'))


@user.route('/settings/expensify_login', methods=['GET', 'POST'])
@login_required
def expensify_login():
    form = ExpensifyAPICredentialsForm(current_user, uid=current_user.id)

    if form.validate_on_submit():
        current_user.expensify_id = request.form.get('partnerUserID')
        current_user.expensify_secret = request.form.get('partnerUserSecret')

        current_user.save()

        flash('Your Expensify API settings have been saved.', 'success')
        return redirect(url_for('user.settings'))

    return render_template('user/expensify_login.html', form=form)


@user.route('/settings/update_locale', methods=['GET', 'POST'])
@login_required
def update_locale():
    form = UpdateLocaleForm(locale=current_user.locale)

    if form.validate_on_submit():
        form.populate_obj(current_user)
        current_user.save()

        flash('Your locale settings have been updated.', 'success')
        return redirect(url_for('user.settings'))

    return render_template('user/update_locale.html', form=form)
