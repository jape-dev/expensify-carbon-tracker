import datetime
import json

import pytest
import pytz
import pandas as pd
from mock import Mock

from config import settings
from canopact.app import create_app
from lib.util_datetime import timedelta_months
from canopact.extensions import db as _db
from canopact.blueprints.carbon.models.carbon import Carbon
from canopact.blueprints.company.models import Company
from canopact.blueprints.carbon.models.expense import Expense
from canopact.blueprints.carbon.models.route import Route
from canopact.blueprints.carbon.models.report import Report
from canopact.blueprints.user.models import User
from canopact.blueprints.billing.models.credit_card import CreditCard
from canopact.blueprints.billing.models.coupon import Coupon
from canopact.blueprints.billing.models.subscription import Subscription
from canopact.blueprints.billing.gateways.stripecom import (
    Coupon as PaymentCoupon,
    Event as PaymentEvent,
    Card as PaymentCard,
    Subscription as PaymentSubscription,
    Invoice as PaymentInvoice,
    Customer as PaymentCustomer,
    Charge as PaymentCharge
)


@pytest.yield_fixture(scope='session')
def app():
    """
    Setup our flask test app, this only gets executed once.

    :return: Flask app
    """
    db_uri = '{0}_test'.format(settings.SQLALCHEMY_DATABASE_URI)
    params = {
        'DEBUG': False,
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': db_uri
    }

    _app = create_app(settings_override=params)

    # Establish an application context before running the tests.
    ctx = _app.app_context()
    ctx.push()

    yield _app

    ctx.pop()


@pytest.yield_fixture(scope='function')
def client(app):
    """
    Setup an app client, this gets executed for each test function.

    :param app: Pytest fixture
    :return: Flask app client
    """
    yield app.test_client()


@pytest.fixture(scope='session')
def db(app):
    """
    Setup our database, this only gets executed once per session.

    :param app: Pytest fixture
    :return: SQLAlchemy database session
    """
    _db.drop_all()
    _db.create_all()

    # Create a single user because a lot of tests do not mutate this user.
    # It will result in faster tests.
    params = {
        'id': 1,
        'role': 'admin',
        'email': 'admin@local.host',
        'password': 'password',
        'coins': 100,
        'company_id': 1
    }

    admin = User(**params)
    company = Company(id=params['company_id'])

    _db.session.add(company)
    _db.session.commit()
    _db.session.add(admin)
    _db.session.commit()

    return _db


@pytest.yield_fixture(scope='function')
def session(db):
    """
    Allow very fast tests by using rollbacks and nested sessions. This does
    require that your database supports SQL savepoints, and Postgres does.

    Read more about this at:
    http://stackoverflow.com/a/26624146

    :param db: Pytest fixture
    :return: None
    """
    db.session.begin_nested()

    yield db.session

    db.session.rollback()


@pytest.fixture(scope='session')
def token(db):
    """
    Serialize a JWS token.

    :param db: Pytest fixture
    :return: JWS token
    """
    user = User.find_by_identity('admin@local.host')
    return user.serialize_token()


@pytest.fixture(scope='function')
def users(db):
    """
    Create user fixtures. They reset per test.

    :param db: Pytest fixture
    :return: SQLAlchemy database session
    """
    db.session.query(Company).delete()
    db.session.query(User).delete()

    users = [
        {
            'id': 1,
            'role': 'admin',
            'email': 'admin@local.host',
            'password': 'password',
            'company_id': 2
        },
        {
            'id': 2,
            'active': False,
            'email': 'disabled@local.host',
            'password': 'password',
            'company_id': 3
        }
    ]

    for user in users:
        db.session.add(Company(id=user['company_id']))
        db.session.commit()
        db.session.add(User(**user))
        db.session.commit()

    return db


@pytest.fixture(scope='function')
def reports(db):
    """
    Create expenses fixtures. They reset per test.

    :param db: Pytest fixture
    :return: SQLAlchemy database session
    """
    db.session.query(Report).delete()

    reports = [
        {
            'report_id': 1,
            'user_id': 1
        },
        {
            'report_id': 2,
            'user_id': 1
        },
    ]

    for report in reports:
        db.session.add(Report(**report))

    db.session.commit()

    return db


@pytest.fixture(scope='function')
def expenses(db):
    """
    Create expenses fixtures. They reset per test.

    :param db: Pytest fixture
    :return: SQLAlchemy database session
    """
    db.session.query(Expense).delete()

    expenses = [
        {
            'expense_id': 1,
            'user_id': 1,
            'report_id': 1,
            'expense_type': 'expense',
            'expense_category': 'Car, Van and Travel Expenses: Air',
            'expense_comment': "Blackfriars, London; Shoreditch, London;"
        },
        {
            'expense_id': 2,
            'user_id': 1,
            'report_id': 1,
            'expense_type': 'expense',
            'expense_category': 'Car, Van and Travel Expenses: Bus',
            'expense_comment': "Blackfriars, London; Shoreditch, London;"
        },
        {
            'expense_id': 3,
            'user_id': 1,
            'report_id': 1,
            'expense_type': 'expense',
            'expense_category': 'Car, Van and Travel Expenses: Taxi',
            'expense_comment': "Blackfriars, London; Shoreditch, London;"
        },
    ]

    for expense in expenses:
        db.session.add(Expense(**expense))

    db.session.commit()

    return db


@pytest.fixture(scope='function')
def carbons(db):
    """
    Create expenses fixtures. They reset per test.

    :param db: Pytest fixture
    :return: SQLAlchemy database session
    """
    db.session.query(Carbon).delete()

    carbons = [
        {
            'expense_id': 1
        },
        {
            'expense_id': 2
        },
    ]

    for carbon in carbons:
        db.session.add(Carbon(**carbon))

    db.session.commit()

    return db


@pytest.fixture(scope='function')
def routes(db):
    """
    Create routes fixtures. They reset per test.

    :param db: Pytest fixture
    :return: SQLAlchemy database session
    """
    db.session.query(Route).delete()

    routes = [
        {
            'expense_id': 1,
            'origin': 'Harrow, London',
            'destination': 'Wembley, London'
        },
        {
            'expense_id': 2,
            'origin': 'Harrow, London',
            'destination': 'London Bridge, London'
        },
    ]

    for route in routes:
        db.session.add(Route(**route))

    db.session.commit()

    return db


@pytest.fixture
def expense_instance():
    exp_attr = {
        'expense_id': 1,
        'user_id': 1,
        'report_id': 1,
        'expense_type': 'Expense',
        'expense_category': 'Car, Van and Travel Expenses: Air',
        'expense_amount': 500.0,
        'expense_currency': 'GBP',
        'expense_comment':  "Blackfriars, London; Shoreditch, London;",
        'expense_converted_amount': None,
        'expense_created_date': None,
        'expense_inserted_date': '2020-06-29',
        'expense_merchant': 'British Airways ',
        'expense_modified_amount': None,
        'expense_modified_created_date': None,
        'expense_modified_merchant': None,
        'expense_unit_count': None,
        'expense_unit_rate': None,
        'expense_unit_unit': None
    }
    return Expense(**exp_attr)


@pytest.fixture
def carbon_instance():
    carbon_attr = {
        'id': 1,
        'expense_id': 1
    }
    return Carbon(**carbon_attr)


@pytest.fixture
def report_instance():
    attr = {
        'report_id': 1,
        'user_id': 1
    }
    return Report(**attr)


@pytest.fixture
def user_instance():
    attr = {
        'id': 1,
        'company_id': 1
    }
    return User(**attr)


@pytest.fixture
def distance_df():

    url1 = ("https://maps.googleapis.com/maps/api/distancematrix/"
            "json?units=metric&mode=driving&origins=Harrow, London&"
            "destinations=Wembley, London&key=fake123")

    url2 = ("https://maps.googleapis.com/maps/api/distancematrix/"
            "json?units=metric&mode=driving&origins=Nou Camp,"
            " Barcelona&destinations=St James's Park, Newcastle&key=fake123")

    data = {
        'expense_id': [1, 2],
        'origin': ['Harrow, London', "Nou Camp, Barcelona"],
        'destination': ['Wembley, London', "St James's Park, Newcastle"],
        'url': [url1, url2]
    }

    return pd.DataFrame(data)


@pytest.fixture
def air_df():

    url1 = "https://www.distance24.org/route.json?stops=Hamburg|Berlin"

    url2 = ("https://www.distance24.org/route.json?stops=London Heathrow"
            "|London Gatwick")

    data = {
        'expense_id': [1, 2],
        'origin': ['Hamburg', 'London Heathrow'],
        'destination': ['Berlin', 'London Gatwick'],
        'url': [url1, url2]
    }

    return pd.DataFrame(data)


@pytest.fixture(scope="function")
def mock_ground_api_response():

    url1 = ("https://maps.googleapis.com/maps/api/distancematrix/"
            "json?units=metric&mode=driving&origins=Harrow, London&"
            "destinations=Wembley, London&key=fake123")

    url2 = ("https://maps.googleapis.com/maps/api/distancematrix/"
            "json?units=metric&mode=driving&origins=Nou Camp,"
            " Barcelona&destinations=St James's Park, Newcastle&key=fake123")

    class MockGoogleApiResponse():
        """Mock response for the Google Distance Matrix API"""
        def __init__(self, *args, **kwargs):
            self.url = args[0]

        def json(self):
            d1 = (
                {
                    'destination_addresses': ['Wembley, UK'],
                    'origin_addresses': ['Harrow, UK'],
                    'rows': [
                                {'elements': [
                                    {'distance': {
                                        'text': '5.6 km',
                                        'value': 5611
                                    },
                                     'duration': {
                                        'text': '11 mins',
                                        'value': 670
                                    }, 'status': 'OK'}
                                    ]}
                            ],
                    'status': 'OK'
                }
            )

            d2 = {
                "destination_addresses": [
                    "St James Park, Newcastle upon Tyne, UK"
                ],
                "origin_addresses": [
                    "C. d'Arístides Maillol, 12, 08028 Barcelona, Spain"
                ],
                "rows": [
                    {
                        "elements": [
                            {
                             "distance": {
                                "text": "1,934 km",
                                "value": 1934300
                             },
                             "duration": {
                                "text": "19 hours 26 mins",
                                "value": 69939
                             },
                             "status": "OK"
                            }
                        ]
                    }
                ],
                "status": "OK"
                }

            if self.url == url1:
                return d1
            if self.url == url2:
                return d2

    return MockGoogleApiResponse


@pytest.fixture(scope='function')
def credit_cards(db):
    """
    Create credit card fixtures.

    :param db: Pytest fixture
    :return: SQLAlchemy database session
    """
    db.session.query(CreditCard).delete()

    may_29_2015 = datetime.date(2015, 5, 29)
    june_29_2015 = datetime.datetime(2015, 6, 29, 0, 0, 0)
    june_29_2015 = pytz.utc.localize(june_29_2015)

    credit_cards = [
        {
            'user_id': 1,
            'brand': 'Visa',
            'last4': 4242,
            'exp_date': june_29_2015
        },
        {
            'user_id': 1,
            'brand': 'Visa',
            'last4': 4242,
            'exp_date': timedelta_months(12, may_29_2015)
        }
    ]

    for card in credit_cards:
        db.session.add(CreditCard(**card))

    db.session.commit()

    return db


@pytest.fixture(scope='function')
def coupons(db):
    """
    Create coupon fixtures.

    :param db: Pytest fixture
    :return: SQLAlchemy database session
    """
    db.session.query(Coupon).delete()

    may_29_2015 = datetime.datetime(2015, 5, 29, 0, 0, 0)
    may_29_2015 = pytz.utc.localize(may_29_2015)

    june_29_2015 = datetime.datetime(2015, 6, 29)
    june_29_2015 = pytz.utc.localize(june_29_2015)

    coupons = [
        {
            'amount_off': 1,
            'redeem_by': may_29_2015
        },
        {
            'amount_off': 1,
            'redeem_by': june_29_2015
        },
        {
            'percent_off': 0.33
        }
    ]

    for coupon in coupons:
        db.session.add(Coupon(**coupon))

    db.session.commit()

    return db


@pytest.fixture(scope='function')
def subscriptions(db):
    """
    Create subscription fixtures.

    :param db: Pytest fixture
    :return: SQLAlchemy database session
    """
    subscriber = User.find_by_identity('subscriber@local.host')
    if subscriber:
        subscriber.delete()
    db.session.query(Subscription).delete()
    db.session.query(Company).delete()

    params = {
        'role': 'admin',
        'email': 'subscriber@local.host',
        'name': 'Subby',
        'password': 'password',
        'payment_id': 'cus_000',
        'company_id': 4

    }

    company = Company(id=params['company_id'])
    subscriber = User(**params)

    # The account needs to be commit before we can assign a subscription to it.
    db.session.add(company)
    db.session.commit()
    db.session.add(subscriber)
    db.session.commit()

    # Create a subscription.
    params = {
        'user_id': subscriber.id,
        'plan': 'gold'
    }
    subscription = Subscription(**params)
    db.session.add(subscription)

    # Create a credit card.
    params = {
        'user_id': subscriber.id,
        'brand': 'Visa',
        'last4': '4242',
        'exp_date': datetime.date(2015, 6, 1)
    }
    credit_card = CreditCard(**params)
    db.session.add(credit_card)

    db.session.commit()

    return db


@pytest.fixture(scope='session')
def mock_stripe():
    """
    Mock all of the Stripe API calls.

    :return:
    """
    PaymentCoupon.create = Mock(return_value={})
    PaymentCoupon.delete = Mock(return_value={})
    PaymentEvent.retrieve = Mock(return_value={})
    PaymentCard.update = Mock(return_value={})
    PaymentSubscription.update = Mock(return_value={})
    PaymentSubscription.cancel = Mock(return_value={})

    # Convert a JSON string into Python attributes.
    #   Source: http://stackoverflow.com/a/25318577
    class AtoD(dict):
        def __init__(self, *args, **kwargs):
            super(AtoD, self).__init__(*args, **kwargs)
            self.__dict__ = self

    customer_api = """{
        "id": "cus_000",
        "sources": {
            "data": [
              {
                "brand": "Visa",
                "exp_month": 6,
                "exp_year": 2023,
                "last4": "4242"
              }
            ]
        }
    }"""
    PaymentCustomer.create = Mock(return_value=json.loads(customer_api,
                                                          object_hook=AtoD))

    upcoming_invoice_api = {
        'date': 1433018770,
        'id': 'in_000',
        'period_start': 1433018770,
        'period_end': 1433018770,
        'lines': {
            'data': [
                {
                    'id': 'sub_000',
                    'object': 'line_item',
                    'type': 'subscription',
                    'livemode': True,
                    'amount': 0,
                    'currency': 'usd',
                    'proration': False,
                    'period': {
                        'start': 1433161742,
                        'end': 1434371342
                    },
                    'subscription': None,
                    'quantity': 1,
                    'plan': {
                        'interval': 'month',
                        'name': 'Gold',
                        'created': 1424879591,
                        'amount': 500,
                        'currency': 'usd',
                        'id': 'gold',
                        'object': 'plan',
                        'livemode': False,
                        'interval_count': 1,
                        'trial_period_days': 14,
                        'metadata': {
                        },
                        'statement_descriptor': 'GOLD MONTHLY'
                    },
                    'description': None,
                    'discountable': True,
                    'metadata': {
                    }
                }
            ],
            'total_count': 1,
            'object': 'list',
            'url': '/v1/invoices/in_000/lines'
        },
        'subtotal': 0,
        'total': 0,
        'customer': 'cus_000',
        'object': 'invoice',
        'attempted': True,
        'closed': True,
        'forgiven': False,
        'paid': True,
        'livemode': False,
        'attempt_count': 0,
        'amount_due': 500,
        'currency': 'usd',
        'starting_balance': 0,
        'ending_balance': 0,
        'next_payment_attempt': None,
        'webhooks_delivered_at': None,
        'charge': None,
        'discount': None,
        'application_fee': None,
        'subscription': 'sub_000',
        'tax_percent': None,
        'tax': None,
        'metadata': {
        },
        'statement_descriptor': None,
        'description': None,
        'receipt_number': None
    }
    PaymentInvoice.upcoming = Mock(return_value=upcoming_invoice_api)

    charge_create_api = {
      'id': 'ch_000',
      'object': 'charge',
      'amount': 825,
      'amount_refunded': 0,
      'application_fee': None,
      'balance_transaction': 'txn_000',
      'captured': True,
      'created': 1461334393,
      'currency': 'usd',
      'customer': 'cus_000',
      'description': None,
      'destination': None,
      'dispute': None,
      'failure_code': None,
      'failure_message': None,
      'fraud_details': {
      },
      'invoice': None,
      'livemode': False,
      'metadata': {
      },
      'order': None,
      'paid': True,
      'receipt_email': None,
      'receipt_number': None,
      'refunded': False,
      'refunds': {
        'object': 'list',
        'data': [

        ],
        'has_more': False,
        'total_count': 0,
        'url': '/v1/charges/ch_000/refunds'
      },
      'shipping': None,
      'source': {
        'id': 'card_000',
        'object': 'card',
        'address_city': None,
        'address_country': None,
        'address_line1': None,
        'address_line1_check': None,
        'address_line2': None,
        'address_state': None,
        'address_zip': None,
        'address_zip_check': None,
        'brand': 'Visa',
        'country': 'US',
        'customer': 'cus_000',
        'cvc_check': 'pass',
        'dynamic_last4': None,
        'exp_month': 12,
        'exp_year': 2030,
        'funding': 'credit',
        'last4': '4242',
        'metadata': {
        },
        'name': None,
        'tokenization_method': None
      },
      'source_transfer': None,
      'statement_descriptor': 'canopact COINS',
      'status': 'succeeded'
    }
    PaymentCharge.create = Mock(return_value=charge_create_api)
