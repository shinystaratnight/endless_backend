import pytest
from django import forms

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError

from r3sourcer.apps.core import models
from r3sourcer.apps.core.utils import form_builder


@pytest.mark.django_db
class TestModelStorageHelperCls:

    @pytest.fixture
    def form_builder(self):
        return models.FormBuilder.objects.create(
            content_type=ContentType.objects.get_for_model(models.Contact),

        )

    @pytest.fixture
    def form(self, company, form_builder):
        return models.Form.objects.create(
            title='test form1',
            builder=form_builder,
            is_active=True,
            company=company
        )

    @pytest.fixture
    def form_field_group(self, form):
        return models.FormFieldGroup.objects.create(
            form=form,
            name='General'
        )

    @pytest.fixture
    def form_fields(self, form_field_group):
        return [
            models.ModelFormField.objects.create(group=form_field_group, name='phone_mobile', required=True),
            models.ModelFormField.objects.create(group=form_field_group, name='email'),
            models.ModelFormField.objects.create(group=form_field_group, name='first_name', required=True)
        ]

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

        assert not related_field.simple_fields
        assert not related_field.related_fields

        related_field.process_field(value)

        assert related_field.value is None
        assert related_field.name == 'contact'
        assert 'first_name' in related_field.simple_fields
        assert related_field.simple_fields['first_name'] == value

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
        assert set(storage_helper.fields['contact'].simple_fields.keys).issuperset({'first_name', 'last_name',
                                                                                    'phone_mobile', 'email'})

        instance = storage_helper.create_instance()
        assert isinstance(instance, models.CompanyContact)
        assert instance.job_title == 'Software Developer'
