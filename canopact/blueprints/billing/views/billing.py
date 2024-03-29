from flask import (
  Blueprint,
  current_app,
  render_template,
  url_for,
  request,
  redirect,
  flash,
)

from flask_login import login_required, current_user
from flask_babel import gettext as _

from config import settings
from lib.util_json import render_json
from canopact.blueprints.billing.forms import SubscriptionForm, \
    UpdateSubscriptionForm, CancelSubscriptionForm
from canopact.blueprints.billing.models.coupon import Coupon
from canopact.blueprints.billing.models.subscription import Subscription
from canopact.blueprints.billing.models.invoice import Invoice
from canopact.blueprints.billing.decorators import subscription_required, \
    handle_stripe_exceptions

billing = Blueprint('billing', __name__, template_folder='../templates',
                    url_prefix='/subscription')


@billing.route('/pricing')
def pricing():
    if current_user.is_authenticated and current_user.subscription:
        return redirect(url_for('billing.update'))

    form = UpdateSubscriptionForm()

    return render_template('billing/pricing.html', form=form,
                           plans=settings.STRIPE_PLANS)


@billing.route('/coupon_code', methods=['POST'])
@login_required
def coupon_code():
    code = request.form.get('coupon_code')
    if code is None:
        return render_json(422,
                           {'error': 'Coupon code cannot be processed.'})

    coupon = Coupon.find_by_code(code)
    if coupon is None:
        return render_json(404, {'error': 'Coupon code not found.'})

    return render_json(200, {'data': coupon.to_json()})


@billing.route('/create', methods=['GET', 'POST'])
@handle_stripe_exceptions
@login_required
def create():
    # Prevent circular import.
    from canopact.blueprints.company.models import Company

    if current_user.subscription:
        flash(_('You already have an active subscription.'), 'info')
        return redirect(url_for('user.settings'))

    plan = request.args.get('plan')
    subscription_plan = Subscription.get_plan_by_id(plan)

    # Guard against an invalid or missing plan.
    if subscription_plan is None and request.method == 'GET':
        flash(_('Sorry, that plan did not exist.'), 'error')
        return redirect(url_for('billing.pricing'))

    stripe_key = current_app.config.get('STRIPE_PUBLISHABLE_KEY')
    form = SubscriptionForm(stripe_key=stripe_key, plan=plan)

    if form.validate_on_submit():
        subscription = Subscription()
        company = Company.query.get(current_user.company_id)
        quantity = company.group_and_count_users()
        created = subscription.create(user=current_user,
                                      company=company,
                                      name=request.form.get('name'),
                                      plan=request.form.get('plan'),
                                      coupon=request.form.get('coupon_code'),
                                      token=request.form.get('stripe_token'))

        if created:
            subscription.add(company, qty=quantity)
            flash(_('Thank you for subscribing.'), 'success')
        else:
            flash(_('You must enable JavaScript for this request.'), 'warning')

        return redirect(url_for('user.settings'))

    return render_template('billing/payment_method.html',
                           form=form, plan=subscription_plan)


@billing.route('/update', methods=['GET', 'POST'])
@handle_stripe_exceptions
@subscription_required
@login_required
def update():
    current_plan = current_user.subscription.plan
    active_plan = Subscription.get_plan_by_id(current_plan)
    new_plan = Subscription.get_new_plan(request.form.keys())

    plan = Subscription.get_plan_by_id(new_plan)

    # Guard against an invalid, missing or identical plan.
    is_same_plan = new_plan == active_plan['id']
    if ((new_plan is not None and plan is None) or is_same_plan) and \
            request.method == 'POST':
        return redirect(url_for('billing.update'))

    form = UpdateSubscriptionForm(coupon_code=current_user.subscription.coupon)

    if form.validate_on_submit():
        subscription = Subscription()
        updated = subscription.update(user=current_user,
                                      coupon=request.form.get('coupon_code'),
                                      plan=plan.get('id'))

        if updated:
            flash(_('Your subscription has been updated.'), 'success')
            return redirect(url_for('user.settings'))

    return render_template('billing/pricing.html',
                           form=form,
                           plans=settings.STRIPE_PLANS,
                           active_plan=active_plan)


@billing.route('/cancel', methods=['GET', 'POST'])
@handle_stripe_exceptions
@login_required
def cancel():
    # Prevent circular import.
    from canopact.blueprints.company.models import Company

    if not current_user.subscription:
        flash(_('You do not have an active subscription.'), 'error')
        return redirect(url_for('user.settings'))

    form = CancelSubscriptionForm()

    if form.validate_on_submit():
        subscription = Subscription()
        company = Company.query.get(current_user.company_id)
        cancelled = subscription.cancel(user=current_user, company=company)

        if cancelled:
            flash(_('Sorry to see you go, your subscription has been '
                    'cancelled.'), 'success')
            return redirect(url_for('user.settings'))

    return render_template('billing/cancel.html', form=form)


@billing.route('/update_payment_method', methods=['GET', 'POST'])
@handle_stripe_exceptions
@login_required
def update_payment_method():
    # Prevent circular import.
    from canopact.blueprints.company.models import Company

    if not current_user.credit_card:
        flash(_('You do not have a payment method on file.'), 'error')
        return redirect(url_for('user.settings'))

    active_plan = Subscription.get_plan_by_id(
        current_user.subscription.plan)

    card = current_user.credit_card
    stripe_key = current_app.config.get('STRIPE_PUBLISHABLE_KEY')
    form = SubscriptionForm(stripe_key=stripe_key,
                            plan=active_plan,
                            name=current_user.name)

    if form.validate_on_submit():
        subscription = Subscription()
        company = Company.query.get(current_user.company_id)
        updated = subscription.update_payment_method(user=current_user,
                                                     company=company,
                                                     credit_card=card,
                                                     name=request.form.get(
                                                         'name'),
                                                     token=request.form.get(
                                                         'stripe_token'))

        if updated:
            flash(_('Your payment method has been updated.'), 'success')
        else:
            flash(_('You must enable JavaScript for this request.'), 'warning')

        return redirect(url_for('user.settings'))

    return render_template('billing/payment_method.html', form=form,
                           plan=active_plan, card_last4=str(card.last4))


@billing.route('/billing_details', defaults={'page': 1})
@billing.route('/billing_details/page/<int:page>')
@handle_stripe_exceptions
@login_required
def billing_details(page):
    paginated_invoices = Invoice.query.filter(
      Invoice.user_id == current_user.id) \
        .order_by(Invoice.created_on.desc()).paginate(page, 12, True)

    if current_user.subscription:
        upcoming = Invoice.upcoming(current_user.payment_id)
        coupon = Coupon.query \
            .filter(Coupon.code == current_user.subscription.coupon).first()
    else:
        upcoming = None
        coupon = None

    return render_template('billing/billing_details.html',
                           paginated_invoices=paginated_invoices,
                           upcoming=upcoming, coupon=coupon)
