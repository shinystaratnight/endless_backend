"""
Django settings for ecore project.

Generated by 'django-admin startproject' using Django 1.10.3.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os

from django.utils.translation import ugettext_lazy as _
from kombu import Queue, Exchange
from endless_logger.conf import *


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    'django_celery_beat',

    'endless_core_utils',
    'endless_core',
    'djangocms_admin_style',
    'admin_shortcuts',
    'django.contrib.admin',

    'loginas',
    'drf_auto_endpoint',
    'export_app',
    'django_filters',
    'cities_light',
    'easy_thumbnails',
    'django_extensions',
    'phonenumber_field',
    'rest_framework',
    'rest_framework_swagger',
    'filer',
    'cms',
    'endless_core_cms',
    'treebeard',
    'menus',
    'sekizai',
    'rosetta',
    'guardian',
    'easy_select2',
    'polymorphic',

    'djangocms_rosetta',
    'classytags',
    'djangocms_text_ckeditor',
    'djangocms_link',
    'djangocms_snippet',
    'djangocms_column',
    'djangocms_grid',
    'djangocms_style',
    'cmsplugin_filer_file',
    'cmsplugin_filer_folder',
    'cmsplugin_filer_link',
    'cmsplugin_filer_image',
    'cmsplugin_filer_teaser',
    'cmsplugin_filer_video',
    'djangocms_file',
    'djangocms_inherit',
    'djangocms_googlemap',
    'djangocms_picture',
    'djangocms_teaser',
    'djangocms_video',
    'djangocms_table',
    'djangocms_oembed',

    'endless_login',
    'endless_logger',
    'endless_acceptance_tests',
    'endless_candidate',
    'endless_skills',
    'endless_pricing',

    'endless_sms_interface',
    'endless_twilio',

    'compressor',
    'djangobower',
    'endless_activity'
]

if 'endless_logger' in INSTALLED_APPS:
    INSTALLED_APPS.append('endless_core_logger')

MIDDLEWARE = [
    'cms.middleware.utils.ApphookReloadMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
    'cms.middleware.language.LanguageCookieMiddleware',
    'crum.CurrentRequestUserMiddleware',
]

ROOT_URLCONF = 'ecore.urls'

SITE_ID = 1

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'ecore', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'sekizai.context_processors.sekizai',
                'cms.context_processors.cms_settings'
            ],
        },
    },
]

WSGI_APPLICATION = 'ecore.wsgi.application'


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
    }
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
    },

}

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

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

CMS_PERMISSION = True
CMS_FALLBACK_LANGUAGE = True

# Need to set your actual domain
SITE_URL = "https://{}".format(env('DOMAIN_NAME', 'localhost'))


CKEDITOR_SETTINGS = {
        'toolbar_Basic': [
            ['Source', '-', 'Bold', 'Italic']
        ],
        'toolbar_YourCustomToolbarConfig': [
            {'name': 'document', 'items': ['Source', '-', 'Save', 'NewPage', 'Preview', 'Print', '-', 'Templates']},
            {'name': 'clipboard', 'items': ['Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo']},
            {'name': 'editing', 'items': ['Find', 'Replace', '-', 'SelectAll']},
            {'name': 'forms',
             'items': ['Form', 'Checkbox', 'Radio', 'TextField', 'Textarea', 'Select', 'Button', 'ImageButton',
                       'HiddenField']},
            '/',
            {'name': 'basicstyles',
             'items': ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript', '-', 'RemoveFormat']},
            {'name': 'paragraph',
             'items': ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote', 'CreateDiv', '-',
                       'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock', '-', 'BidiLtr', 'BidiRtl',
                       'Language']},
            {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
            {'name': 'insert',
             'items': ['Image', 'Flash', 'Table', 'HorizontalRule', 'Smiley', 'SpecialChar', 'PageBreak', 'Iframe']},
            '/',
            {'name': 'styles', 'items': ['Styles', 'Format', 'Font', 'FontSize']},
            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
            {'name': 'tools', 'items': ['Maximize', 'ShowBlocks']},
            {'name': 'about', 'items': ['About']},
            {'name': 'yourcustomtools', 'items': [
                'Preview',
                'Maximize'
            ]},
        ],
        'toolbar': 'YourCustomToolbarConfig',
        'tabSpaces': 4,
}

# TODO: GRID

DJANGOCMS_GRID_CONFIG = {
    'COLUMNS': 24,
    'TOTAL_WIDTH': 960,
    'GUTTER': 20,
}

# TODO: COLUMN
COLUMN_WIDTH_CHOICES = (
    ('10%', _("10%")),
    ('20%', _("20%")),
    ('25%', _("25%")),
    ('33.33%', _('33%')),
    ('50%', _("50%")),
    ('66.66%', _('66%')),
    ('75%', _("75%")),
    ('100%', _('100%')),
)

FILER_CANONICAL_URL = 'sharing/'


TEXT_SAVE_IMAGE_FUNCTION = 'cmsplugin_filer_image.integrations.ckeditor.create_image_plugin'

CMS_TEMPLATES = (
    ("base_structured.html", _("Structured")),
)

CMSPLUGIN_FILER_IMAGE_STYLE_CHOICES = (
    ('default', _('Default')),
    ('boxed', _('Boxed'))
)

CMSPLUGIN_FILER_IMAGE_DEFAULT_STYLE = 'boxed'

THUMBNAIL_HIGH_RESOLUTION = True

DJANGOCMS_STYLE_TAGS = [
    'div', 'article', 'section', 'header', 'footer', 'aside', 'nav', 'main', 'span', 'a', 'p' 'h1', 'h2', 'h3', 'h4',
    'h5', 'h6', 'ul', 'li'
]

DJANGOCMS_SNIPPET_SEARCH = True

DJANGOCMS_GOOGLEMAP_API_KEY = env('GOOGLE_GEO_CODING_API_KEY')


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
        'micro': {'size': (40, 40), 'crop': True},
        'small': {'size': (120, 120), 'crop': True},
        'medium': {'size': (240, 240), 'crop': True},
        'large': {'size': (480, 480), 'crop': True},
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

REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'endless_core.api.filters.ApiOrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'endless_core.api.pagination.ApiLimitOffsetPagination',
    'DEFAULT_METADATA_CLASS': 'endless_core.api.metadata.ApiMetadata',
    'PAGE_SIZE': 10,
    'DATETIME_INPUT_FORMATS': ['iso-8601'],
    'EXCEPTION_HANDLER': 'endless_core.api.views.core_exception_handler',
}

ADMIN_SHORTCUTS = [
    {
        'title': _("CMS"),
        'shortcuts': [
            {
                'url': '/',
                'open_new_window': True,
            },
            {
                'url_name': 'admin:cms_page_changelist',
                'title': _('Pages'),
                'count_new': 'endless_core_cms.counters.page_counter'
            },
            {
                'url_name': 'admin:filer_folder_changelist',
                'title': _('Files'),
            },
            {
                'url_name': 'admin:cms_pageuser_changelist',
                'title': _('Users'),
            },
            {
                'url_name': 'admin:djangocms_snippet_snippet_changelist',
                'title': _('Snippets'),
            },
        ]
    },
]

CMS_ENABLE_UPDATE_CHECK = True

GOOGLE_GEO_CODING_API_KEY = env('GOOGLE_GEO_CODING_API_KEY', '')

# ENDLESS_CORE APP

AUTH_USER_MODEL = 'endless_core.User'
AUTHENTICATION_BACKENDS = [
    'endless_core.backends.ContactBackend',
    'guardian.backends.ObjectPermissionBackend',
]
CITIES_LIGHT_APP_NAME = 'endless_core'
LOGINAS_REDIRECT_URL = '/admin'
ANONYMOUS_USER_NAME = None

# DRF schema adapter
DRF_AUTO_BASE_SERIALIZER = 'endless_core.api.serializers.ApiBaseModelSerializer'
DRF_AUTO_BASE_VIEWSET = 'endless_core.api.viewsets.BaseApiViewset'
DRF_AUTO_DEFAULT_ENDPOINT_CLASS = 'endless_core.api.endpoints.ApiEndpoint'
DRF_AUTO_METADATA_ADAPTER = 'endless_core.api.metadata.AngularApiAdapter'

DRF_AUTO_WIDGET_MAPPING = {
    'ApiDateTimeTzField': 'datetime',
}

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

LOGGER_DB = env('LOGGER_DB', LOGGER_DB)
LOGGER_USER = env('LOGGER_USER', LOGGER_USER)
LOGGER_PASSWORD = env('LOGGER_PASSWORD', LOGGER_PASSWORD)
LOGGER_HOST = env('LOGGER_HOST', LOGGER_HOST)
LOGGER_PORT = env('LOGGER_PORT', LOGGER_PORT)

# FIXME: change system user email
SYSTEM_USER = "system@endless.pro"
SYSTEM_MASTER_COMPANY = "LabourKing"

OPENEXCHANGE_APP_ID = env('OPENEXCHANGE_APP_ID', '')

# bower configuration
BOWER_COMPONENTS_ROOT = root('var', 'www')

BOWER_INSTALLED_APPS = (
    'font-awesome',
    'jquery-ui',
    'bootstrap#3.3.7'
)

DEFAULT_CURRENCY = 'USD'

DELIVERY_TIMEOUT_SMS = 10   # sms no delivered within X minutes
REPLY_TIMEOUT_SMS = 20   # recipient does not reply within X minutes
