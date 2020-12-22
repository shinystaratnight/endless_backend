"""
Django settings for r3sourcer project.

Generated by 'django-admin startproject' using Django 1.10.3.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

from datetime import timedelta
from decimal import Decimal

from django.utils.translation import ugettext_lazy as _
from timezonefinder import TimezoneFinder


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def env(key, default=None):
    return os.environ.get(key, default)


def root(*dirs):
    return os.path.join(BASE_DIR, *dirs)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DJANGO_DEBUG", '1') == '1'
TEST = False

ALLOWED_HOSTS = [x.strip() for x in env('ALLOWED_HOSTS').split(',')]

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_celery_results',

    'r3sourcer.apps.core_utils',
    'r3sourcer.apps.core',
    'django.contrib.admin',

    'loginas',
    'django_filters',
    'cities_light',
    'easy_thumbnails',
    'django_extensions',
    'phonenumber_field',
    'rest_framework',
    'filer',
    'mptt',
    'rosetta',
    'guardian',
    'easy_select2',
    'polymorphic',
    'corsheaders',

    'r3sourcer.importer',
    'r3sourcer.apps.sms_interface',
    'r3sourcer.apps.email_interface',
    'r3sourcer.apps.twilio',
    'r3sourcer.apps.login',
    'r3sourcer.apps.logger',
    'r3sourcer.apps.acceptance_tests',
    'r3sourcer.apps.candidate',
    'r3sourcer.apps.skills',
    'r3sourcer.apps.pricing',
    'r3sourcer.apps.hr',
    'r3sourcer.apps.activity',
    'r3sourcer.apps.myob',
    'r3sourcer.apps.company_settings',
    'r3sourcer.apps.billing',

    'oauth2_provider',
    'oauth2_provider_jwt',
    'compressor',
    'djangobower',
    'rest_framework_swagger',
]

if 'r3sourcer.apps.logger' in INSTALLED_APPS:
    INSTALLED_APPS.append('r3sourcer.apps.core_logger')

    from r3sourcer.apps.logger.conf import *

    LOGGER_DB = env('LOGGER_DB', LOGGER_DB)
    LOGGER_USER = env('LOGGER_USER', LOGGER_USER)
    LOGGER_PASSWORD = env('LOGGER_PASSWORD', LOGGER_PASSWORD)
    LOGGER_HOST = env('LOGGER_HOST', LOGGER_HOST)
    LOGGER_PORT = env('LOGGER_PORT', LOGGER_PORT)

    LOGGER_ENABLED = env('LOGGER_ENABLED', '1') == '1'


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'oauth2_provider.middleware.OAuth2TokenMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'crum.CurrentRequestUserMiddleware',
]

ROOT_URLCONF = 'r3sourcer.urls'

SITE_ID = 1

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'r3sourcer', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'r3sourcer.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': env('POSTGRES_DB'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PASSWORD'),
        'HOST': env('POSTGRES_HOST'),
        'PORT': str(env('POSTGRES_PORT')),
    },
    'import': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'pepro',
        'USER': 'crm',
        'PASSWORD': 'ax9b22axax',
        'HOST': env('POSTGRES_HOST'),
        'PORT': str(env('POSTGRES_PORT')),
    },
}

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://{host}:{port}/1'.format(
            host=env('REDIS_HOST'),
            port=env('REDIS_PORT')
        ),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': env('CACHE_KEY_PREFIX')
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/
DEFAULT_LANGUAGE = 'en'
LANGUAGE_CODE = 'en-au'

TIME_ZONE = env('TIME_ZONE')

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

DJANGO_STUFF_URL_PREFIX = env('DJANGO_STUFF_URL_PREFIX', '')

STATIC_URL = '/{}static/'.format(DJANGO_STUFF_URL_PREFIX)
MEDIA_URL = '/{}media/'.format(DJANGO_STUFF_URL_PREFIX)

MEDIA_ROOT = root('var', 'www', 'media')
STATIC_ROOT = root('var', 'www', 'static')

LANGUAGES = [
    (LANGUAGE_CODE, _('English')),
]

# Need to set your actual domain
SITE_URL = "https://{}".format(env('DOMAIN_NAME', 'localhost'))
REDIRECT_DOMAIN = env('REDIRECT_DOMAIN', 'localhost')

FILER_CANONICAL_URL = 'sharing/'


THUMBNAIL_HIGH_RESOLUTION = True

SILENCED_SYSTEM_CHECKS = ["fields.W342"]

THUMBNAIL_PROCESSORS = (
    'easy_thumbnails.processors.colorspace',
    'easy_thumbnails.processors.autocrop',
    # 'easy_thumbnails.processors.scale_and_crop',
    'filer.thumbnail_processors.scale_and_crop_with_subject_location',
    'easy_thumbnails.processors.filters',
)

THUMBNAIL_ALIASES = {
    '': {
        'micro': {'size': (40, 40), 'autocrop': True, 'crop': False},
        'small': {'size': (120, 120), 'autocrop': True, 'crop': False},
        'medium': {'size': (240, 240), 'autocrop': True, 'crop': False},
        'large': {'size': (480, 480), 'autocrop': True, 'crop': False},
    },
}

CELERY_RESULT_BACKEND = 'django-db'

CELERY_BROKER_URL = 'amqp://{host}:{port}//'.format(
    host=env('RABBIT_MQ_HOST'),
    port=env('RABBIT_MQ_PORT'),
)

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_EVENT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

CELERYBEAT_SCHEDULE = {}

CELERY_QUEUES = (
    # TODO: create
    # Queue('example', Exchange('example'), routing_key='example')
)

CELERY_ROUTES = {}
CELERY_IMPORTS = (
    'core.tasks',
)

REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_FILTER_BACKENDS': (
        'r3sourcer.apps.core.api.permissions.SiteMasterCompanyFilterBackend',
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'r3sourcer.apps.core.api.filters.ApiOrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'r3sourcer.apps.core.api.pagination.ApiLimitOffsetPagination',
    'PAGE_SIZE': 10,
    'DATETIME_INPUT_FORMATS': ['iso-8601'],
    'EXCEPTION_HANDLER': 'r3sourcer.apps.core.api.views.core_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'r3sourcer.apps.core.api.authentication.JWTAuthentication',
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        'r3sourcer.apps.core.api.permissions.SiteContactPermissions',
    )
}

GOOGLE_GEO_CODING_API_KEY = env('GOOGLE_GEO_CODING_API_KEY', '')
GOOGLE_DISTANCE_MATRIX_API_KEY = env('GOOGLE_DISTANCE_MATRIX_API_KEY', '')

# CORE APP

AUTH_USER_MODEL = 'core.User'
AUTHENTICATION_BACKENDS = [
    'oauth2_provider.backends.OAuth2Backend',
    'r3sourcer.apps.core.backends.ContactBackend',
    'guardian.backends.ObjectPermissionBackend',
]
CITIES_LIGHT_APP_NAME = 'core'
LOGINAS_REDIRECT_URL = '/admin'
ANONYMOUS_USER_NAME = None

BASE_SERIALIZER = 'r3sourcer.apps.core.api.serializers.ApiBaseModelSerializer'
BASE_VIEWSET = 'r3sourcer.apps.core.api.viewsets.BaseApiViewset'
BASE_READONLY_VIEWSET = 'r3sourcer.apps.core.api.viewsets.BaseApiViewset'
DEFAULT_ENDPOINT_CLASS = 'r3sourcer.apps.core.api.endpoints.ApiEndpoint'
ROUTER_CLASS = 'r3sourcer.apps.core.api.router.ApiRouter'
INFLECTOR_LANGUAGE = 'inflector.English'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'djangobower.finders.BowerFinder',
    'compressor.finders.CompressorFinder',
)

COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.rCSSMinFilter',
]

COMPRESS_ENABLED = True

# FIXME: change system user email
SYSTEM_USER = "system@endless.pro"
SYSTEM_MASTER_COMPANY = env('SYSTEM_MASTER_COMPANY', 'TS MEDIA Pty Ltd T/A LABOURKING')

OPENEXCHANGE_APP_ID = env('OPENEXCHANGE_APP_ID', '')

# bower configuration
BOWER_COMPONENTS_ROOT = root('var', 'www')

BOWER_INSTALLED_APPS = (
    'font-awesome#4.5.0',
    'jquery-ui',
    'bootstrap#3.3.7'
)

DEFAULT_CURRENCY = 'AUD'
REPLY_TIMEOUT_SMS = 4
DELIVERY_TIMEOUT_SMS = 4
GOING_TO_WORK_SMS_DELAY_MINUTES = 90

ENABLED_TWILIO_WORKING = False

SMS_SERVICE_ENABLED = env('SMS_SERVICE_ENABLED', '0') == '1'
SMS_SERVICE_CLASS = env('SMS_SERVICE_CLASS', 'r3sourcer.apps.sms_interface.services.FakeSMSService')

FETCH_ADDRESS_RAISE_EXCEPTIONS = env('FETCH_ADDRESS_RAISE_EXCEPTIONS', '0') == '1'

DATE_FORMAT = 'd/m/Y'
DATE_MYOB_FORMAT = 'Y-m-d'
DATE_INPUT_FORMATS = [
    '%d/%m/%Y', '%Y-%m-%d',     # '25/10/2006', '2006-10-25'
    '%b %d %Y', '%b %d, %Y',    # 'Oct 25 2006', 'Oct 25, 2006'
    '%d %b %Y', '%d %b, %Y',    # '25 Oct 2006', '25 Oct, 2006'
    '%B %d %Y', '%B %d, %Y',    # 'October 25 2006', 'October 25, 2006'
    '%d %B %Y', '%d %B, %Y',    # '25 October 2006', '25 October, 2006'
]

DATETIME_FORMAT = 'd/m/Y h:i A'
DATETIME_MYOB_FORMAT = 'Y-m-d H:i:s'
DATETIME_INPUT_FORMATS = [
    '%d/%m/%Y %H:%M',        # '10/25/2006 14:30'
    '%d/%m/%Y %I:%M %p',     # '10/25/2006 2:30 PM'
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M:%S.%f',  # '2006-10-25 14:30:59.000200'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
]

TIME_FORMAT = 'h:i A'
TIME_INPUT_FORMATS = [
    '%H:%M',        # '14:30'
    '%H:%M:%S',     # '14:30:59'
    '%H:%M:%S.%f',  # '14:30:59.000200'
]

MYOB_APP = {
    'desc': env('MYOB_APP_DESC', 'MYOB'),
    'api_key': env('MYOB_APP_API_KEY'),
    'api_secret': env('MYOB_APP_API_SECRET'),
    'api_key_ssl': env('MYOB_APP_API_KEY_SSL'),
    'api_secret_ssl': env('MYOB_APP_API_SECRET_SSL'),
}

EMAIL_SERVICE_ENABLED = env('EMAIL_SERVICE_ENABLED', '0') == '1'
EMAIL_SERVICE_CLASS = env('EMAIL_SERVICE_CLASS', 'r3sourcer.apps.email_interface.services.SMTPEmailService')

NO_REPLY_EMAIL = 'R3soucer Software'

DEFAULT_SMTP_SERVER = env('DEFAULT_SMTP_SERVER', 'smtp.gmail.com')
DEFAULT_SMTP_PORT = env('DEFAULT_SMTP_PORT', 587)
DEFAULT_SMTP_EMAIL = env('DEFAULT_SMTP_EMAIL', NO_REPLY_EMAIL)
DEFAULT_SMTP_PASSWORD = env('DEFAULT_SMTP_PASSWORD', '')
DEFAULT_SMTP_TLS = env('DEFAULT_SMTP_TLS', '1') == '1'

# time delta in hours
VACANCY_FILLING_TIME_DELTA = 8

ENABLED_MYOB_WORKING = env('ENABLED_MYOB_WORKING', '0') == '1'


CITIES_LIGHT_CITY_SOURCES = [
    'http://download.geonames.org/export/dump/cities15000.zip',
    'http://download.geonames.org/export/dump/AU.zip',
]

CITIES_LIGHT_INCLUDE_CITY_TYPES = [
    'PPL', 'PPLA', 'PPLA2', 'PPLA3', 'PPLA4', 'PPLC', 'PPLF', 'PPLG', 'PPLL', 'PPLR', 'PPLS', 'STLMT', 'PPLX'
]


SUPERVISOR_DECLINE_TIMEOUT = 4 * 60 * 60
JOBSITE_NOT_ACTIVE_TIMEOUT = 60 * 60 * 24 * 180


QUERYSET_CLASS = env('QUERYSET_CLASS', 'r3sourcer.apps.core.managers.AbstractObjectOwnerQuerySet')


# Stripe settings
STRIPE_PUBLIC_API_KEY = env('STRIPE_PUBLIC_API_KEY')
STRIPE_SECRET_API_KEY = env('STRIPE_SECRET_API_KEY')
STRIPE_PRODUCT_ID = env('STRIPE_PRODUCT_ID')

MONTHLY_EXTRA_WORKER_FEE = 13
ANNUAL_EXTRA_WORKER_FEE = 10

COST_OF_SMS_SEGMENT = Decimal('0.08')
SMS_SEGMENT_SIZE = 160


def CAN_LOGIN_AS(request, target_user): return request.user


CORS_ORIGIN_REGEX_WHITELIST = (
    r'^(https?://)?(\w+\.)?r3sourcer(test)?\.com$',
    r'^(https?://)?r3sourcersoft(test)?\.com$',
)

if DEBUG:
    CORS_ORIGIN_REGEX_WHITELIST += (r'^(http?://)?(\w+\.)?localhost$', )

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=3),
}

JWT_ISSUER = 'R3sourcerIssuer'
JWT_ID_ATTRIBUTE = 'username'

OAUTH2_PROVIDER = {
    'OAUTH2_BACKEND_CLASS': 'oauth2_provider.oauth2_backends.JSONOAuthLibCore',
}

sentry_sdk.init(
    dsn="{}".format(env('SENTRY_DSN')),
    integrations=[DjangoIntegration(), CeleryIntegration()]
)

try:
    with open(root(env('JWT_RS256_PRIVATE_KEY_PATH')), 'r') as jwt_secret:
        JWT_PRIVATE_KEY_R3SOURCERISSUER = jwt_secret.read()
except FileNotFoundError:
    print('Please specify path to JWT RSA256 private key')

try:
    with open(root(env('JWT_RS256_PUBLIC_KEY_PATH')), 'r') as jwt_public:
        JWT_PUBLIC_KEY_R3SOURCERISSUER = jwt_public.read()
except FileNotFoundError:
    print('Please specify path to JWT RSA256 public key')

TIME_ZONE_FINDER = TimezoneFinder(in_memory=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'INFO',
            'handlers': ['console'],
        },
    },
}

DEFAULT_PHONE_NUMBER_COUNTRY_CODE = 'AU'
MAXIMUM_ACCEPTANCE_TEST_PICTURES = 2
SUBSCRIPTION_START_WORKERS = 5
SUBSCRIPTION_DEFAULT_DISCOUNT = 0.75
