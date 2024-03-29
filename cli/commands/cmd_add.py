import click
import random

from datetime import datetime

from faker import Faker

from canopact.app import create_app
from canopact.extensions import db
from canopact.blueprints.user.models import User
from canopact.blueprints.carbon.models.expense import Expense
from canopact.blueprints.billing.models.invoice import Invoice

# Create an app context for the database connection.
app = create_app()
db.app = app

fake = Faker()


def _log_status(count, model_label):
    """
    Log the output of how many records were created.

    :param count: Amount created
    :type count: int
    :param model_label: Name of the model
    :type model_label: str
    :return: None
    """
    click.echo('Created {0} {1}'.format(count, model_label))

    return None


def _bulk_insert(model, data, label):
    """
    Bulk insert data to a specific model and log it. This is much more
    efficient than adding 1 row at a time in a loop.

    :param model: Model being affected
    :type model: SQLAlchemy
    :param data: Data to be saved
    :type data: list
    :param label: Label for the output
    :type label: str
    :param skip_delete: Optionally delete previous records
    :type skip_delete: bool
    :return: None
    """
    with app.app_context():
        model.query.delete()

        db.session.commit()
        db.engine.execute(model.__table__.insert(), data)

        _log_status(model.query.count(), label)

    return None


@click.group()
def cli():
    """ Add items to the database. """
    pass


@click.command()
def users():
    """
    Generate fake users.
    """
    random_emails = []
    data = []

    click.echo('Working...')

    # Ensure we get about 100 unique random emails.
    for i in range(0, 99):
        random_emails.append(fake.email())

    random_emails.append(app.config['SEED_ADMIN_EMAIL'])
    random_emails = list(set(random_emails))

    while True:
        if len(random_emails) == 0:
            break

        fake_datetime = fake.date_time_between(
            start_date='-1y', end_date='now').strftime('%s')

        created_on = datetime.utcfromtimestamp(
            float(fake_datetime)).strftime('%Y-%m-%dT%H:%M:%S Z')

        random_percent = random.random()

        if random_percent >= 0.05:
            role = 'member'
        else:
            role = 'admin'

        email = random_emails.pop()

        fake_datetime = fake.date_time_between(
            start_date='-1y', end_date='now').strftime('%s')

        current_sign_in_on = datetime.utcfromtimestamp(
            float(fake_datetime)).strftime('%Y-%m-%dT%H:%M:%S Z')

        params = {
            'created_on': created_on,
            'updated_on': created_on,
            'role': role,
            'email': email,
            'password': User.encrypt_password('password'),
            'sign_in_count': random.random() * 100,
            'current_sign_in_on': current_sign_in_on,
            'current_sign_in_ip': fake.ipv4(),
            'last_sign_in_on': current_sign_in_on,
            'last_sign_in_ip': fake.ipv4()
        }

        # Ensure the seeded admin is always an admin with the seeded password.
        if email == app.config['SEED_ADMIN_EMAIL']:
            password = User.encrypt_password(app.config['SEED_ADMIN_PASSWORD'])

            params['role'] = 'admin'
            params['password'] = password

        data.append(params)

    return _bulk_insert(User, data, 'users')


@click.command()
def invoices():
    """
    Generate random invoices.
    """
    data = []

    users = db.session.query(User).all()

    for user in users:
        for i in range(0, random.randint(1, 12)):
            # Create a fake unix timestamp in the future.
            created_on = fake.date_time_between(
                start_date='-1y', end_date='now').strftime('%s')
            period_start_on = fake.date_time_between(
                start_date='now', end_date='+1y').strftime('%s')
            period_end_on = fake.date_time_between(
                start_date=period_start_on, end_date='+14d').strftime('%s')
            exp_date = fake.date_time_between(
                start_date='now', end_date='+2y').strftime('%s')

            created_on = datetime.utcfromtimestamp(
                float(created_on)).strftime('%Y-%m-%dT%H:%M:%S Z')
            period_start_on = datetime.utcfromtimestamp(
                float(period_start_on)).strftime('%Y-%m-%d')
            period_end_on = datetime.utcfromtimestamp(
                float(period_end_on)).strftime('%Y-%m-%d')
            exp_date = datetime.utcfromtimestamp(
                float(exp_date)).strftime('%Y-%m-%d')

            plans = ['GROW']
            cards = ['Visa', 'Mastercard', 'AMEX',
                     'J.C.B', "Diner's Club"]

            params = {
                'created_on': created_on,
                'updated_on': created_on,
                'user_id': user.id,
                'receipt_number': fake.md5(),
                'description': '{0} MONTHLY'.format(random.choice(plans)),
                'period_start_on': period_start_on,
                'period_end_on': period_end_on,
                'currency': 'usd',
                'tax': random.random() * 100,
                'tax_percent': random.random() * 10,
                'total': random.random() * 1000,
                'brand': random.choice(cards),
                'last4': random.randint(1000, 9000),
                'exp_date': exp_date
            }

            data.append(params)

    return _bulk_insert(Invoice, data, 'invoices')


@click.command()
def expenses():
    """Generate random expenses and save to database.

    """
    data = []

    users = db.session.query(User).all()

    for user in users:
        for i in range(0, 300):
            # Create a fake unix timestamp in the future.
            created_on = fake.date_time_between(
                start_date='-1y', end_date='-18d')

            created_on_datetime = created_on.strftime('%Y-%m-%dT%H:%M:%S Z')
            created_on_date = created_on.strftime('%Y-%m-%d')

            merchants = ['National Train Company', 'Car Hire', 'Taxi Company',
                         'Bus Company']
            categories = ["Car, Van and Travel Expenses: Train",
                          "Car, Van and Travel Expenses: Fuel",
                          "Car, Van and Travel Expenses: Taxi",
                          "Car, Van and Travel Expenses: Bus",
                          "Car, Van and Travel Expenses: Car Hire"]
            comments = ['London, UK; Newcastle, UK;',
                        'Southampton, UK; Cambridge, UK;',
                        'Sunderland, UK; Newcastle, UK;',
                        'Cambridge, UK; Oxford, UK;',
                        'London, UK; Reading, UK;',
                        'Reading, UK; London, UK;',
                        'Warwick, UK; Durham, UK;',
                        'Oxford, UK; London, UK;',
                        'Birmingham, UK; London, UK;',
                        'Banbury, UK; Southampton, UK;',
                        'Durham, UK; Sunderland, UK;',
                        'Coventry, UK; Banbury, UK;',
                        'Newport, UK; Oxford, UK;']

            params = {
                'created_on': created_on_datetime,
                'updated_on': created_on_datetime,
                'expense_id': int(random.random()*1000000000),
                'user_id': 1,
                'report_id': 72282405,
                'expense_type': 'expense',
                'expense_category': random.choice(categories),
                'expense_amount': 52,
                'expense_currency': 'GBP',
                'expense_comment': random.choice(comments),
                'expense_converted_amount': None,
                'expense_created_date': created_on_date,
                'expense_inserted_date': created_on_date,
                'expense_merchant': random.choice(merchants),
                'expense_modified_amount': None,
                'expense_modified_created_date': None,
                'expense_modified_merchant': None,
                'expense_unit_count': None,
                'expense_unit_rate': None,
                'expense_unit_unit': None,
                'travel_expense': 1,
            }

            data.append(params)

    return _bulk_insert(Expense, data, 'expenses')


@click.command()
@click.pass_context
def all(ctx):
    """
    Generate all data.

    :param ctx:
    :return: None
    """
    ctx.invoke(users)
    ctx.invoke(invoices)

    return None


cli.add_command(users)
cli.add_command(invoices)
cli.add_command(expenses)
cli.add_command(all)
