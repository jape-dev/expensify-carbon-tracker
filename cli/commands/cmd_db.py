import base64
import datetime
import click
import io
import pandas as pd
from pathlib import Path
import paramiko
from sqlalchemy_utils import database_exists, create_database
from sshtunnel import SSHTunnelForwarder

from canopact.app import create_app
from canopact.extensions import db
from canopact.blueprints.user.models import User
from canopact.blueprints.company.models import Company


# Create an app context for the database connection.
app = create_app()
db.app = app


@click.group()
def cli():
    """ Run PostgreSQL related tasks. """
    pass


@click.command()
@click.option('--with-testdb/--no-with-testdb', default=False,
              help='Create a test db too?')
def init(with_testdb):
    """
    Initialize the database.

    :param with_testdb: Create a test database
    :return: None

    TODO:
        * Figure out why route model is not being created w/o import.

    """
    from canopact.blueprints.carbon.models.activity import Activity
    from canopact.blueprints.carbon.models.route import Route
    from canopact.blueprints.company.models import Company

    db.drop_all()
    db.create_all()
    print(db.engine.table_names())

    if with_testdb:
        db_uri = '{0}_test'.format(app.config['SQLALCHEMY_DATABASE_URI'])

        if not database_exists(db_uri):
            create_database(db_uri)

    return None


@click.command()
def remote_init():
    """
    Initialize the databas remotely using SSH tunnelling.

    :param with_testdb: Create a test database
    :return: None

    """
    from canopact.blueprints.carbon.models.activity import Activity
    from canopact.blueprints.carbon.models.route import Route
    from canopact.blueprints.company.models import Company

    hostname = app.config['SSH_HOSTNAME']
    ssh_username = app.config['SSH_USERNAME']
    instance_key_path = app.config['INSTANCE_KEY_PATH']
    remote_address = app.config['REMOTE_ADDRESS']
    remote_port = app.config['REMOTE_PORT']
    db_pass = app.config['DB_PASS']
    db_user = app.config['DB_USER']

    # Decode key back into a useable form from base64.
    with open(Path(instance_key_path), 'rb') as f:
        blob = base64.b64encode(f.read())

    instance_key = blob.decode('utf-8')

    key_decoded = base64.b64decode(instance_key)
    ssh_key = key_decoded.decode('utf-8')

    # Pass key to parmiko to get your pkey
    pkey = paramiko.RSAKey.from_private_key(io.StringIO(ssh_key))

    with SSHTunnelForwarder(
        hostname,
        ssh_username=ssh_username,
        ssh_pkey=pkey,
        remote_bind_address=(remote_address, remote_port)
            ) as tunnel:

        tunnel.start()

        db_uri = (f'postgres://{db_user}:{db_pass}'
                  f'@localhost:{tunnel.local_bind_port}/canopactdb-1')

        app.config['SQLALCHEMY_DATABASE_URI'] = str(db_uri)
        db.drop_all()
        db.create_all()
        print(db.engine.table_names())

    return None


@click.command()
def upload():
    """
    Upload data into remote database with records that are in:
    /canopact/upload/upload.csv

    Returns:
        None

    """
    from canopact.blueprints.carbon.models.expense import Expense
    from canopact.blueprints.carbon.models.report import Report

    hostname = app.config['SSH_HOSTNAME']
    ssh_username = app.config['SSH_USERNAME']
    instance_key_path = app.config['INSTANCE_KEY_PATH']
    remote_address = app.config['REMOTE_ADDRESS']
    remote_port = app.config['REMOTE_PORT']
    db_pass = app.config['DB_PASS']
    db_user = app.config['DB_USER']
    db_name = app.config['DB_NAME']
    upload_path = app.config['UPLOAD_PATH']

    # Decode key back into a useable form from base64.
    with open(Path(instance_key_path), 'rb') as f:
        blob = base64.b64encode(f.read())

    instance_key = blob.decode('utf-8')

    key_decoded = base64.b64decode(instance_key)
    ssh_key = key_decoded.decode('utf-8')

    # Pass key to parmiko to get your pkey
    pkey = paramiko.RSAKey.from_private_key(io.StringIO(ssh_key))

    # Use SSH tunnel to connect to remote database.
    with SSHTunnelForwarder(
        hostname,
        ssh_username=ssh_username,
        ssh_pkey=pkey,
        remote_bind_address=(remote_address, remote_port)
            ) as tunnel:

        tunnel.start()

        db_uri = (f'postgres://{db_user}:{db_pass}'
                  f'@localhost:{tunnel.local_bind_port}/{db_name}')

        app.config['SQLALCHEMY_DATABASE_URI'] = str(db_uri)

        # Ingest file path as a pandas dataframe.
        file_path = Path(upload_path)
        data = pd.read_csv(file_path)

        if data.empty:
            print('Upload.csv file contained no records.')

            return None

        else:
            # Iterate over each row in the dataframe.
            for i, row in data.iterrows():
                email = row['email']
                transport_type = row['transport_type']
                comment = row['comment']
                cost = row['cost']
                currency = row['currency']
                merchant = row['merchant']
                date = row['date']
                date = datetime.datetime.strptime(str(date), '%d/%m/%Y').date()

                # Use email address to get user record.
                u = User.find_by_identity(email)

                # Create and save a report record.
                r = Report()
                r.user_id = u.id
                r.save()

                # Create and save a expense record.
                row = {
                    'report_id': r.report_id,
                    'user_id': u.id,
                    'expense_type': 'expense',
                    'expense_category': transport_type,
                    'expense_comment': comment,
                    'expense_merchant': merchant,
                    'expense_currency': currency,
                    'expense_amount': cost,
                    'expense_converted_amount': cost,
                    'expense_created_date': date,
                    'expense_inserted_date': date
                }

                e = Expense(**row)
                e.save()

            print('Records succesfully uploaded to database.')

            return None


@click.command()
def seed():
    """
    Seed the database with an initial user.

    :return: User instance
    """
    if User.find_by_identity(app.config['SEED_ADMIN_EMAIL']) is not None:
        return None

    company_params = {
        'id': app.config['SEED_COMPANY_ID']
    }

    Company(**company_params).save()

    user_params = {
        'role': 'company_admin',
        'email': app.config['SEED_ADMIN_EMAIL'],
        'password': app.config['SEED_ADMIN_PASSWORD'],
        'company_id': app.config['SEED_COMPANY_ID'],
        'expensify_id': app.config['SEED_EXPENSIFY_ID'],
        'expensify_secret': app.config['SEED_EXPENSIFY_TOKEN']
    }

    u = User(**user_params)
    u.email_confirmed = app.config['SEED_EMAIL_CONFIRMED']

    return u.save()


@click.command()
@click.argument('table', default='None')
def drop(table):
    """Drop database tables.

    Args:
        tables: name of table to drop. If None, drop all tables.

    """
    if table != 'None':

        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        engine = db.create_engine(db_uri)

        m = db.MetaData()
        m.reflect(bind=engine)

        table_name = m.tables[table]
        m.drop_all(engine, tables=[table_name])
        print(f'Successfully dropped {table}')
    else:
        print(f'Dropping tables: {db.engine.table_names()}')
        db.drop_all()
        print('Successfully dropped all tables.')

    return None


@click.command()
@click.option('--with-testdb/--no-with-testdb', default=False,
              help='Create a test db too?')
@click.pass_context
def reset(ctx, with_testdb):
    """
    Init and seed automatically.

    :param with_testdb: Create a test database
    :return: None
    """
    ctx.invoke(init, with_testdb=with_testdb)
    ctx.invoke(seed)

    return None


cli.add_command(init)
cli.add_command(upload)
cli.add_command(remote_init)
cli.add_command(seed)
cli.add_command(drop)
cli.add_command(reset)
