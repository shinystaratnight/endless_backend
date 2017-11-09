import mock
import pytest

from r3sourcer.apps.logger.manager import get_endless_logger

from r3sourcer.apps.core.models import (
    User
)
from r3sourcer.apps.login.models import TokenLogin


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='test@test.tt', phone_mobile='+12345678901',
        password='test1234'
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email='test42@test.tt', phone_mobile='+12345678942',
        password='test4242'
    )


@pytest.fixture
def contact(db, user):
    return user.contact


@pytest.fixture
@mock.patch('r3sourcer.apps.login.mixins.get_random_string', return_value='1'*8)
def token_login(mock_gen_token, contact):
    return TokenLogin.objects.create(contact=contact)


@pytest.fixture(autouse=True, scope='module')
def clickhouse_restart():
    logger = get_endless_logger()
