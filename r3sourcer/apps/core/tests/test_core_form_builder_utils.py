import pytest

from django.contrib.contenttypes.models import ContentType

from r3sourcer.apps.core import models
from r3sourcer.apps.core.utils import form_builder


@pytest.mark.django_db
class TestModelStorageHelperCls:

    def test_simple_field(self):
        name, value = 'test_name', 'test value'
        simple_field = form_builder.SimpleFieldHelper(name, value)
        assert simple_field.name == name
        assert simple_field.value == value

        with pytest.raises(AssertionError):
            form_builder.SimpleFieldHelper('test-invalid-name', value)

        with pytest.raises(AssertionError):
            form_builder.SimpleFieldHelper('0test', value)

        with pytest.raises(AssertionError):
            form_builder.SimpleFieldHelper('-test', value)

    def test_related_field(self):
        value = 'test value'
        related_field = form_builder.RelatedFieldHelper(models.CompanyContact, 'contact__first_name', value)

        assert related_field.value is None
        assert related_field.name == 'contact'
        assert 'first_name' in related_field.simple_fields
        assert related_field.simple_fields['first_name'].value == value

        with pytest.raises(AssertionError):
            related_field.process_field(value)

    def test_storage_helper(self):
        storage_helper = form_builder.StorageHelper(models.CompanyContact, {
            'job_title': 'Software Developer',
            'contact__first_name': 'first name',
            'contact__last_name': 'last name',
            'contact__email': 'test@example.com',
            'contact__phone_mobile': '+79998887766'
        })
        storage_helper.process_fields()

        assert set(storage_helper.fields.keys()).issuperset({'contact', 'job_title'})
        assert set(storage_helper.fields['contact'].simple_fields.keys()).issuperset({'first_name', 'last_name',
                                                                                      'phone_mobile', 'email'})

        instance = storage_helper.create_instance()
        assert isinstance(instance, models.CompanyContact)
        assert instance.job_title == 'Software Developer'
