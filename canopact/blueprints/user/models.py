import datetime
from collections import OrderedDict
from hashlib import md5

import pytz
from flask import current_app, url_for
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash

from flask_login import UserMixin

from itsdangerous import URLSafeTimedSerializer, \
    TimedJSONWebSignatureSerializer

from lib.util_sqlalchemy import ResourceMixin, AwareDateTime, tzware_datetime
from canopact.blueprints.billing.models.credit_card import CreditCard
from canopact.blueprints.billing.models.subscription import Subscription
from canopact.blueprints.billing.models.invoice import Invoice
from canopact.blueprints.carbon.models.activity import Activity
from canopact.blueprints.carbon.models.report import Report
from canopact.extensions import db
from vendors import salesforce
from vendors.salesforce import SalesforceOAuth2


class User(UserMixin, ResourceMixin, db.Model):
    ROLE = OrderedDict([
        ('member', 'Member'),
        ('company_admin', 'Company Admin'),
        ('admin', 'Admin')
    ])

    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)

    # Relationships.
    credit_card = db.relationship(CreditCard, uselist=False, backref='users',
                                  passive_deletes=True)
    subscription = db.relationship(Subscription, uselist=False,
                                   backref='users', passive_deletes=True)
    invoices = db.relationship(Invoice, backref='users', passive_deletes=True)
    reports = db.relationship(Report, backref='reports', passive_deletes=True)
    activities = db.relationship(Activity, backref='reports',
                                 passive_deletes=True)

    # Authentication.
    role = db.Column(db.Enum(*ROLE, name='role_types', native_enum=False),
                     index=True, nullable=False, server_default='company_admin'
                     )
    active = db.Column('is_active', db.Boolean(), nullable=False,
                       server_default='1')
    email = db.Column(db.String(255), unique=True, index=True, nullable=False,
                      server_default='')
    password = db.Column(db.String(128), nullable=False, server_default='')
    email_confirmation_sent_on = db.Column(AwareDateTime(), nullable=True)
    email_confirmed = db.Column(db.Boolean(), nullable=True, default=False)
    email_confirmed_on = db.Column(AwareDateTime(), nullable=True)

    # Company.
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id',
                                                     onupdate='CASCADE',
                                                     ondelete='CASCADE'),
                           index=True, nullable=False)
    job_title = db.Column(db.String(128))

    # Billing.
    name = db.Column(db.String(128), index=True)
    payment_id = db.Column(db.String(128), index=True)
    cancelled_subscription_on = db.Column(AwareDateTime())
    previous_plan = db.Column(db.String(128))

    # Activity tracking.
    sign_in_count = db.Column(db.Integer, nullable=False, default=0)
    current_sign_in_on = db.Column(AwareDateTime())
    current_sign_in_ip = db.Column(db.String(45))
    last_sign_in_on = db.Column(AwareDateTime())
    last_sign_in_ip = db.Column(db.String(45))

    # Salesforce.
    sf_instance_url = db.Column(db.String(128))
    sf_access_token = db.Column(db.String(128))
    sf_refresh_token = db.Column(db.String(128))
    sf_token_activated_on = db.Column(db.String(128))

    # Expensify.
    expensify_id = db.Column(db.String(128))
    expensify_secret = db.Column(db.String(128))

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(User, self).__init__(**kwargs)

        self.password = User.encrypt_password(kwargs.get('password', ''))
        self.email_confirmation_sent_on = None
        self.email_confirmed = False
        self.email_confirmed_on = None

    @classmethod
    def find_by_identity(cls, identity):
        """
        Find a user by their e-mail.

        :param identity: Email.
        :type identity: str
        :return: User instance
        """
        return User.query.filter(User.email == identity).first()

    @classmethod
    def encrypt_password(cls, plaintext_password):
        """
        Hash a plaintext string using PBKDF2. This is good enough according
        to the NIST (National Institute of Standards and Technology).

        In other words while bcrypt might be superior in practice, if you use
        PBKDF2 properly (which we are), then your passwords are safe.

        :param plaintext_password: Password in plain text
        :type plaintext_password: str
        :return: str
        """
        if plaintext_password:
            return generate_password_hash(plaintext_password)

        return None

    @classmethod
    def deserialize_token(cls, token):
        """
        Obtain a user from de-serializing a signed token.

        :param token: Signed token.
        :type token: str
        :return: User instance or None
        """
        private_key = TimedJSONWebSignatureSerializer(
            current_app.config['SECRET_KEY'])
        try:
            decoded_payload = private_key.loads(token)

            return User.find_by_identity(decoded_payload.get('user_email'))
        except Exception:
            return None

    @classmethod
    def initialize_password_reset(cls, identity):
        """
        Generate a token to reset the password for a specific user.

        :param identity: User e-mail address or username
        :type identity: str
        :return: User instance
        """

        u = User.find_by_identity(identity)
        reset_token = u.serialize_token()

        server_name = current_app.config['TEMP_SERVER_NAME']
        current_app.config['SERVER_NAME'] = server_name

        reset_url = url_for(
            'user.password_reset',
            token=reset_token,
            _external=True)

        current_app.config['SERVER_NAME'] = None

        # This prevents circular imports.
        from canopact.blueprints.user.tasks import (
            deliver_password_reset_email)
        deliver_password_reset_email.delay(u.id, reset_url)

        return u

    @classmethod
    def initialize_email_confirmation(cls, identity):
        """
        Generate a token to authenticate email when registering.

        :param identity: User e-mail address or username
        :type identity: str
        :return: User instance
        """

        u = User.find_by_identity(identity)
        auth_token = u.get_auth_token()

        server_name = current_app.config['TEMP_SERVER_NAME']
        current_app.config['SERVER_NAME'] = server_name

        confirm_url = url_for(
            'user.confirm_email',
            token=auth_token,
            _external=True)

        current_app.config['SERVER_NAME'] = None

        # This prevents circular imports.
        from canopact.blueprints.user.tasks import (
            deliver_confirmation_email)
        deliver_confirmation_email.delay(u.id, confirm_url)

        return u

    @classmethod
    def search(cls, query):
        """
        Search a resource by 1 or more fields.

        :param query: Search query
        :type query: str
        :return: SQLAlchemy filter
        """
        if not query:
            return ''

        search_query = '%{0}%'.format(query)
        search_chain = (User.email.ilike(search_query))

        return or_(*search_chain)

    @classmethod
    def is_last_admin(cls, user, new_role, new_active):
        """
        Determine whether or not this user is the last admin account.

        :param user: User being tested
        :type user: User
        :param new_role: New role being set
        :type new_role: str
        :param new_active: New active status being set
        :type new_active: bool
        :return: bool
        """
        is_changing_roles = user.role == 'admin' and new_role != 'admin'
        is_changing_active = user.active is True and new_active is None

        if is_changing_roles or is_changing_active:
            admin_count = User.query.filter(User.role == 'admin').count()
            active_count = User.query.filter(User.is_active is True).count()

            if admin_count == 1 or active_count == 1:
                return True

        return False

    @classmethod
    def bulk_delete(cls, ids):
        """
        Override the general bulk_delete method because we need to delete them
        one at a time while also deleting them on Stripe.

        :param ids: List of ids to be deleted
        :type ids: list
        :return: int
        """
        delete_count = 0

        for id in ids:
            user = User.query.get(id)

            if user is None:
                continue

            if user.payment_id is None:
                user.delete()
            else:
                subscription = Subscription()
                cancelled = subscription.cancel(user=user)

                # If successful, delete it locally.
                if cancelled:
                    user.delete()

            delete_count += 1

        return delete_count

    def is_active(self):
        """
        Return whether or not the user account is active, this satisfies
        Flask-Login by overwriting the default value.

        :return: bool
        """
        return self.active

    def get_auth_token(self):
        """
        Return the user's auth token. Use their password as part of the token
        because if the user changes their password we will want to invalidate
        all of their logins across devices. It is completely fine to use
        md5 here as nothing leaks. Company id is also included.

        This satisfies Flask-Login by providing a means to create a token.

        :return: str
        """
        private_key = current_app.config['SECRET_KEY']

        serializer = URLSafeTimedSerializer(private_key)
        data = [str(self.id),
                str(self.company_id),
                md5(self.password.encode('utf-8')).hexdigest()]

        return serializer.dumps(data)

    def authenticated(self, with_password=True, password=''):
        """
        Ensure a user is authenticated, and optionally check their password.

        :param with_password: Optionally check their password
        :type with_password: bool
        :param password: Optionally verify this as their password
        :type password: str
        :return: bool
        """
        if with_password:
            return check_password_hash(self.password, password)

        return True

    def serialize_token(self, expiration=3600):
        """
        Sign and create a token that can be used for things such as resetting
        a password or other tasks that involve a one off token.

        :param expiration: Seconds until it expires, defaults to 1 hour
        :type expiration: int
        :return: JSON
        """
        private_key = current_app.config['SECRET_KEY']

        serializer = TimedJSONWebSignatureSerializer(private_key, expiration)
        return serializer.dumps({'user_email': self.email}).decode('utf-8')

    def update_activity_tracking(self, ip_address):
        """
        Update various fields on the user that's related to meta data on their
        account, such as the sign in count and ip address, etc..

        :param ip_address: IP address
        :type ip_address: str
        :return: SQLAlchemy commit results
        """
        self.sign_in_count += 1

        self.last_sign_in_on = self.current_sign_in_on
        self.last_sign_in_ip = self.current_sign_in_ip

        self.current_sign_in_on = datetime.datetime.now(pytz.utc)
        self.current_sign_in_ip = ip_address

        return self.save()

    def update_salesforce_token(self):
        """
        Updates the sf access token for a new session. Saves to self.

        Returns:
            access_token (str): access token for the current sf session.

        """
        # Retrieve a new access token using the refresh token.
        id, secret, uri = salesforce.get_config()
        oauth = SalesforceOAuth2(id, secret, uri)
        tokens = oauth.get_access_token_refresh(self.sf_refresh_token)
        instance_url = tokens.json().get("instance_url")
        access_token = tokens.json().get("access_token")

        # Update the access token in db.
        self.sf_access_token = access_token
        self.sf_token_activated_on = tzware_datetime()
        self.save()

        return instance_url, access_token
