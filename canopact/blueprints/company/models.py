"""Models for company

Author: James Patten
First Build: October 2020

"""

import datetime
import pytz

from canopact.extensions import db
from canopact.blueprints.user.models import User
from flask import current_app, url_for
from lib.util_sqlalchemy import ResourceMixin, AwareDateTime
from lib.util_datetime import timedelta_months, datediff_days, tzware_datetime


class Company(ResourceMixin, db.Model):
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    employees = db.Column(db.String(20))
    industry = db.Column(db.String(50))
    country = db.Column(db.String(128))
    free_trial_expires_on = db.Column(AwareDateTime())
    trial_active = db.Column(db.Boolean(), default=True)

    # Billing.
    billing_name = db.Column(db.String(128), index=True)
    payment_id = db.Column(db.String(128), index=True)
    cancelled_subscription_on = db.Column(AwareDateTime())
    previous_plan = db.Column(db.String(128))
    subscriptions = db.Column(db.Integer)

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Company, self).__init__(**kwargs)
        self.free_trial_expires_on = self.set_trial_expiry()

    def set_trial_expiry(self):
        """Sets self.free_trial_expires_on when class is instantiated.

        Returns:
            datetime.datetime: free trial expiry date.

        """

        if not self.free_trial_expires_on:
            expires = timedelta_months(1, self.created_on)
        else:
            expires = self.free_trial_expires_on

        return expires

    @staticmethod
    def initialize_invite(to_email, from_email):
        """
        Generate a url to invite and authenticate a user for registering.

        Args:
            to_email (str): email of receipient user.
            from_email (str): email of sender user.
        """

        u = User.find_by_identity(from_email)
        auth_token = u.get_auth_token()

        server_name = current_app.config['TEMP_SERVER_NAME']
        current_app.config['SERVER_NAME'] = server_name

        invite_url = url_for(
            'company.invite_signup',
            token=auth_token,
            email=to_email,
            _external=True)

        current_app.config['SERVER_NAME'] = None

        # This prevents circular imports.
        from canopact.blueprints.company.tasks import (
            deliver_invite_email)
        deliver_invite_email.delay(to_email, from_email, invite_url)

    def days_left_on_trial(self, start=None, end=None):
        """
        Get the number of days left on the free trial.

        Args:
            Start (datetime.datetime): when free trial started.
            End (datetime.datetime): when free trial ends.

        Returns:
            int: number of days remaining on the trial.

        """
        now = tzware_datetime()

        if not start:
            start = self.created_on
        if not end:
            end = self.free_trial_expires_on

        if end < now:
            days = 0
        else:
            days = datediff_days(start, end)

        return days

    def expire_free_trials(compare_datetime=None):
        """
        Inactivate free trials once they have reached their expiry date.

        compare_datetime (datetime.datetime): datetime to compare the free
            trial expiry date with.

        """
        if compare_datetime is None:
            compare_datetime = datetime.datetime.now(pytz.utc)

        Company.query.filter(
            Company.free_trial_expires_on <= compare_datetime) \
            .update({Company.trial_active: not Company.trial_active})

        return db.session.commit()

    def group_and_count_users(self):
        """
        Perform a group by/count on all users.

        :return: dict
        """
        # Get list of users that belong to company.
        users = User.query.filter(User.company_id == self.id)

        return users.count()
