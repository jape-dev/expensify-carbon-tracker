from flask import Blueprint, render_template, request, flash, redirect, url_for
from canopact.blueprints.page.forms import WaitingListForm

page = Blueprint('page', __name__, template_folder='templates')


@page.route('/', methods=['GET', 'POST'])
def home():
    """ Route to the home page.

    Calls:
        page.tasks.deliver_register_email()

    Returns:
        flask.render_template() for homepage endpoint.
    """
    form = WaitingListForm()

    if form.validate_on_submit():
        from canopact.blueprints.page.tasks import deliver_register_email
        email = request.form.get('email')
        deliver_register_email(email)

        flash('Thank you for registering your interest with Canopact. '
              'We will keep you posted on product progress.', 'success')
        return redirect(url_for('page.home'))

    return render_template('page/home.html', form=form)


@page.route('/terms')
def terms():
    """ Route to the terms page.

    Returns:
        flask.render_template() for terms page endpoint.

    """
    return render_template('page/terms.html')


@page.route('/privacy')
def privacy():
    """ Route to the privacy page.

    Returns:
        flask.render_template() for privacy page endpoint.

    """
    return render_template('page/privacy.html')
