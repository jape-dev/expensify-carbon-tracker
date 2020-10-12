"""Models for company

Author: James Patten
First Build: October 2020

"""

from canopact.extensions import db
from canopact.blueprints.user.models import User
from flask import url_for
from lib.util_sqlalchemy import ResourceMixin


class Company(ResourceMixin, db.Model):

    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Company, self).__init__(**kwargs)

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

        invite_url = url_for(
            'company.invite_signup',
            token=auth_token,
            email=to_email,
            _external=True)

        # This prevents circular imports.
        from canopact.blueprints.company.tasks import (
            deliver_invite_email)
        deliver_invite_email.delay(to_email, from_email, invite_url)
