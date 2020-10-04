from datetime import timedelta


DEBUG = True
LOG_LEVEL = 'DEBUG'  # CRITICAL / ERROR / WARNING / INFO / DEBUG

SERVER_NAME = 'local.docker:8000'
SECRET_KEY = 'insecurekeyfordev'

# Flask-Mail.
MAIL_DEFAULT_SENDER = 'james@canopact.com'
MAIL_SERVER = 'smtp.zoho.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False
MAIL_USERNAME = 'james@canopact.com'
MAIL_PASSWORD = 'test'

# Flask-Babel.
LANGUAGES = {
    'en': 'English',
    'kl': 'Klingon',
    'es': 'Spanish'
}
BABEL_DEFAULT_LOCALE = 'en'

# Celery.
CELERY_BROKER_URL = 'redis://:devpassword@redis:6379/0'
REDBEAT_REDIS_URL = CELERY_BROKER_URL
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_REDIS_MAX_CONNECTIONS = 5
CELERYBEAT_SCHEDULE = {
    'fetch-expensify-reports': {
        'task': 'canopact.blueprints.carbon.tasks.fetch_reports',
        'schedule': 10
    },
    'calculate-carbon': {
        'task': 'canopact.blueprints.carbon.tasks.calculate_carbon',
        'schedule': 10
    }
}

# SQLAlchemy.
db_uri = 'postgresql://canopact:devpassword@postgres:5432/canopact'
SQLALCHEMY_DATABASE_URI = db_uri
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Expensify.
SEED_EXPENSIFY_ID = 'fake_id',
SEED_EXPENSIFY_TOKEN = 'fake_token'

# User.
SEED_ADMIN_EMAIL = 'dev@local.host'
SEED_ADMIN_PASSWORD = 'devpassword'
REMEMBER_COOKIE_DURATION = timedelta(days=90)

# Google Distance Matrix API.
DISTANCE_URL = 'https://maps.googleapis.com/maps/api/distancematrix/json?'
DISTANCE_KEY = 'fake123'
DISTANCE_UNIT = 'metric'

# Distance 24 API.
DISTANCE_24_URL = 'https://www.distance24.org/route.json?'

# DEFRA Emission Factors.
EF_CO2E_CAR = 0.1714
EF_CO2E_TAXI = 0.20369
EF_CO2E_TRAIN = 0.03694
EF_CO2E_AIR_SHORT = 0.15553
EF_CO2E_AIR_LONG = 0.19085
EF_CO2E_AIR_DOMESTIC = 0.2443
EF_CO2E_BUS_LOCAL = 0.10312
EF_CO2E_BUS_COACH = 0.02732

EF_CO2_CAR = 0.17015
EF_CO2_TAXI = 0.20185
EF_CO2_TRAIN = 0.03659
EF_CO2_AIR_SHORT = 0.15475
EF_CO2_AIR_LONG = 0.18989
EF_CO2_AIR_DOMESTIC = 0.24298
EF_CO2_BUS_LOCAL = 0.10231
EF_CO2_BUS_COACH = 0.02679

EF_CH4_CAR = 0.00016
EF_CH4_TAXI = 0.00000349
EF_CH4_TRAIN = 0.00006
EF_CH4_AIR_SHORT = 0.00001
EF_CH4_AIR_LONG = 0.00001
EF_CH4_AIR_DOMESTIC = 0.00011
EF_CH4_BUS_LOCAL = 0.00002
EF_CH4_BUS_COACH = 0.00001

EF_N2O_CAR = 0.00109
EF_N2O_TAXI = 0.00184
EF_N2O_TRAIN = 0.00006
EF_N2O_AIR_SHORT = 0.00077
EF_N2O_AIR_LONG = 0.00095
EF_N2O_AIR_DOMESTIC = 0.00121
EF_N2O_BUS_LOCAL = 0.00079
EF_N2O_BUS_COACH = 0.00052

DEFRA_EMISSION_FACTORS = {
    'co2e': {
        'air': {
            'long': EF_CO2E_AIR_LONG,
            'short': EF_CO2E_AIR_SHORT,
            'domestic': EF_CO2E_AIR_DOMESTIC
        },
        'bus': {
            'local': EF_CO2E_BUS_LOCAL,
            'coach': EF_CO2E_BUS_COACH
        },
        'train': EF_CO2E_TRAIN,
        'car': EF_CO2E_CAR,
        'taxi': EF_CO2E_TAXI
    },
    'co2': {
        'air': {
            'long': EF_CO2_AIR_LONG,
            'short': EF_CO2_AIR_SHORT,
            'domestic': EF_CO2_AIR_DOMESTIC
        },
        'bus': {
            'local': EF_CO2_BUS_LOCAL,
            'coach': EF_CO2_BUS_COACH
        },
        'train': EF_CO2_TRAIN,
        'car': EF_CO2_CAR,
        'taxi': EF_CO2_TAXI
    },
    'ch4': {
        'air': {
            'long': EF_CH4_AIR_LONG,
            'short': EF_CH4_AIR_SHORT,
            'domestic': EF_CH4_AIR_DOMESTIC
        },
        'bus': {
            'local': EF_CH4_BUS_LOCAL,
            'coach': EF_CH4_BUS_COACH
        },
        'train': EF_CH4_TRAIN,
        'car': EF_CH4_CAR,
        'taxi': EF_CH4_TAXI
    },
    'n2o': {
        'air': {
            'long': EF_N2O_AIR_LONG,
            'short': EF_N2O_AIR_SHORT,
            'domestic': EF_N2O_AIR_DOMESTIC
        },
        'bus': {
            'local': EF_N2O_BUS_LOCAL,
            'coach': EF_N2O_BUS_COACH
        },
        'train': EF_N2O_TRAIN,
        'car': EF_N2O_CAR,
        'taxi': EF_N2O_TAXI
    }
}

# Billing.
STRIPE_SECRET_KEY = None
STRIPE_PUBLISHABLE_KEY = None
STRIPE_API_VERSION = '2016-03-07'
STRIPE_CURRENCY = 'usd'
STRIPE_PLANS = {
    '0': {
        'id': 'bronze',
        'name': 'Bronze',
        'amount': 100,
        'currency': STRIPE_CURRENCY,
        'interval': 'month',
        'interval_count': 1,
        'trial_period_days': 14,
        'statement_descriptor': 'canopact BRONZE',
        'metadata': {
            'coins': 110
        }
    },
    '1': {
        'id': 'gold',
        'name': 'Gold',
        'amount': 500,
        'currency': STRIPE_CURRENCY,
        'interval': 'month',
        'interval_count': 1,
        'trial_period_days': 14,
        'statement_descriptor': 'canopact GOLD',
        'metadata': {
            'coins': 600,
            'recommended': True
        }
    },
    '2': {
        'id': 'platinum',
        'name': 'Platinum',
        'amount': 1000,
        'currency': STRIPE_CURRENCY,
        'interval': 'month',
        'interval_count': 1,
        'trial_period_days': 14,
        'statement_descriptor': 'canopact PLATINUM',
        'metadata': {
            'coins': 1500
        }
    }
}

COIN_BUNDLES = [
    {'coins': 100, 'price_in_cents': 100, 'label': '100 for $1'},
    {'coins': 1000, 'price_in_cents': 900, 'label': '1,000 for $9'},
    {'coins': 5000, 'price_in_cents': 4000, 'label': '5,000 for $40'},
    {'coins': 10000, 'price_in_cents': 7000, 'label': '10,000 for $70'},
]

# Bet.
DICE_ROLL_PAYOUT = {
    '2': 36.0,
    '3': 18.0,
    '4': 12.0,
    '5': 9.0,
    '6': 7.2,
    '7': 6.0,
    '8': 7.2,
    '9': 9.0,
    '10': 12.0,
    '11': 18.0,
    '12': 36.0
}

RATELIMIT_STORAGE_URL = CELERY_BROKER_URL
RATELIMIT_STRATEGY = 'fixed-window-elastic-expiry'
RATELIMIT_HEADERS_ENABLED = True
