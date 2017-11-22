from .prod import *


TEST = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': env('POSTGRES_DB'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PASSWORD'),
        'HOST': env('POSTGRES_HOST'),
        'PORT': str(env('POSTGRES_PORT')),
    },
}

LOGGER_DB = 'testing'
LOGGER_ENABLED = False


def cities_light_uri(n): return 'file://%s' % os.path.join(
    BASE_DIR, 'r3sourcer/apps/core/tests/fixtures/django_cities', n
)

CITIES_LIGHT_COUNTRY_SOURCES = [
    cities_light_uri('country.txt')
]

CITIES_LIGHT_REGION_SOURCES = [
    cities_light_uri('regions.txt')
]

CITIES_LIGHT_CITY_SOURCES = [
    cities_light_uri('cities.txt')
]

CITIES_LIGHT_TRANSLATION_SOURCES = [
    cities_light_uri('translations.txt')
]
