import pytest

from django.db import models


class NameModel(models.Model):
    name = models.CharField(max_length=20)


class ModelForAutodiscover(models.Model):
    name = models.CharField(max_length=20)
    rel = models.ForeignKey(NameModel, null=True)

    @classmethod
    def use_logger(cls):
        return True


@pytest.fixture()
def test_model_for_autodiscover(db):
    return ModelForAutodiscover


@pytest.fixture()
def test_instance(db):
    obj = NameModel.objects.create(name='test name')
    return obj


@pytest.fixture()
def test_model(db):
    return NameModel


@pytest.fixture()
def user(db):
    from django.contrib.auth.models import User
    return User.objects.create_superuser("test user", email="test@test.com", password="TestPASS12")
