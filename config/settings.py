from datetime import timedelta
from celery.schedules import crontab


DEBUG = False
LOG_LEVEL = 'DEBUG'  # CRITICAL / ERROR / WARNING / INFO / DEBUG


TEMP_SERVER_NAME = 'localhost:8000'
SERVER_NAME = 'localhost:8000'
SECRET_KEY = 'insecurekeyfordev'

# Flask-Mail.
MAIL_DEFAULT_SENDER = 'james@canopact.com'
MAIL_SERVER = 'smtp.zoho.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False
MAIL_USERNAME = 'james@canopact.com'
MAIL_PASSWORD = 'test'

# Company Sign Up.
EMPLOYEES = {
    '1-10': '1-10 employees',
    '11-20': '11-20 employees',
    '21-99': '21-99 employees',
    '100-199': '100-199 employees',
    '200-749': '200-749 employees',
    '750-1999': '750-1999 employees',
    '2000+': '2000+ employees',
}

INDUSTRIES = {
    'Please Select': 'Please Select',
    'Agriculture': 'Agriculture',
    'Charity & Non-Governmental-Organisations': 'Charity & Non-Governmental-Organisations',
    'Media & Communications': 'Media & Communications',
    'Construction': 'Construction',
    'Consulting & Professional Services': 'Consulting & Professional Services',
    'Defense': 'Defense',
    'E-commerce & Technology': 'E-commerce & Technology',
    'Education': 'Education',
    'Electronics': 'Electronics',
    'Energy & Natural Resources': 'Energy & Natural Resources',
    'Finance, Insurance & Real Estate': 'Finance, Insurance & Real Estate',
    'Health': 'Health',
    'Industrial & Manufacturing': 'Industrial & Manufacturing',
    'Law and Lobbying': 'Law and Lobbying',
    'Leisure & Hospitality': 'Leisure & Hospitality',
    'Transportation': 'Transportation',
    'Other': 'Other'
}

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
        'schedule': 5
    },
    'calculate-carbon': {
        'task': 'canopact.blueprints.carbon.tasks.calculate_carbon',
        'schedule': 5
    },
    'expire-free-trials': {
        'task': 'canopact.blueprints.company.tasks.expire_free_trials',
        'schedule': crontab(hour=0, minute=1)
    }
}

# SQLAlchemy.
db_uri = 'postgresql://canopact:devpassword@postgres:5432/canopact'
SQLALCHEMY_DATABASE_URI = db_uri
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Caching.
CACHE_TYPE = 'SimpleCache'
# CACHE_DIR = '/tmp'
CACHE_DEFAULT_TIMEOUT = 300

# Salesforce.
SF_CLIENT_ID = None
SF_CLIENT_SECRET = None
SF_REDIRECT_URI = 'https://local.docker:8000/oauth2/callback'

# Expensify.
SEED_EXPENSIFY_ID = 'fake_id',
SEED_EXPENSIFY_TOKEN = 'fake_token'

# User.
SEED_ADMIN_EMAIL = 'dev@local.host'
SEED_ADMIN_PASSWORD = 'devpassword'
SEED_COMPANY_ID = '999999999'
SEED_EMAIL_CONFIRMED = True
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

# Manual Uploads
UPLOAD_PATH = '/canopact/upload/upload.csv'

# Billing.
STRIPE_SECRET_KEY = None
STRIPE_PUBLISHABLE_KEY = None
STRIPE_API_VERSION = '2016-03-07'
STRIPE_CURRENCY = 'gbp'
STRIPE_PLANS = {
    '0': {
        'id': 'grow',
        'name': 'Grow',
        'amount': 800,
        'currency': STRIPE_CURRENCY,
        'interval': 'month',
        'interval_count': 1,
        'statement_descriptor': 'canopact GROW',
        'metadata': {
            'recommended': False
        }
    }
}

RATELIMIT_STORAGE_URL = CELERY_BROKER_URL
RATELIMIT_STRATEGY = 'fixed-window-elastic-expiry'
RATELIMIT_HEADERS_ENABLED = True
