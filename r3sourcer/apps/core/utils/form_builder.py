import re

from django.db import models
from django.db import transaction
from django.forms import ModelForm, ValidationError

from rest_framework import exceptions


__all__ = [
    'StorageHelper', 'SimpleFieldHelper', 'RelatedFieldHelper'
]


class StorageHelper(object):
    """
    Helper class for form builder.
    Would be use for creating new objects from Form Builder.
    """

    __slots__ = ['_model', '_fields', '_source_fields', '_done', '_instance', '_validated_fields', '_errors', '_form']

    LOOKUP_SEPARATOR = '__'

    def __init__(self, model, fields: dict):
        assert issubclass(model, models.Model), "`model` should be models.Model subclass"

        self._model = model
        self._source_fields = fields
        self._fields = {}
        self._done = False
        self._instance = None
        self._errors = None
        self._form = None

    def process_fields(self):
        """

        :return:
        """
        for field_name, field_value in self._source_fields.items():
            if self.LOOKUP_SEPARATOR in field_name:
                field = RelatedFieldHelper(self._model, field_name, field_value)
                if field.name in self._fields:
                    old_field = self._fields.get(field.name)
                    RelatedFieldHelper.merge(old_field, field)
                else:
                    self._fields.setdefault(field.name, field)
            else:
                self._fields.setdefault(field_name, SimpleFieldHelper(field_name, field_value))

    def validate(self, raise_errors=False):
        """
        Validate fields
        :return:
        """
        fields_to_validate = {}
        self._errors = {}
        related_fields = {}
        for name, field in self._fields.items():
            try:
                if isinstance(field, RelatedFieldHelper):
                    field.save_related(name)
                    related_fields[name] = field
                    value = field.value.id
                else:
                    value = field.value

                fields_to_validate.setdefault(name, value)
            except exceptions.ValidationError as e:
                self._errors.update({k.replace('__', '.'): v for k, v in e.detail.items()})

        meta_class = type('Meta', (object, ), {
            'model': self._model,
            'fields': [name for name, field in fields_to_validate.items()]
        })

        form = type('MForm', (ModelForm, ), {
            'Meta': meta_class,
        })

        self._form = form(fields_to_validate)

        is_valid = self._form.is_valid()
        if not is_valid:
            self._errors.update({k.replace('__', '.'): v for k, v in self._form.errors.items()})

            for name, field in related_fields.items():
                field.value.delete()

            if raise_errors:
                raise exceptions.ValidationError(self._errors)

        return is_valid and not self._errors

    @transaction.atomic
    def create_instance(self):
        """
        Create instance using fields (RelatedFields and SimpleFields)

        :return: self.model instance.
        """
        assert self._instance is None, 'Instance already created'
        assert self._form is not None, 'Need to run `.validate()` first'
        assert not self._errors, 'Form invalid'

        self._instance = self._form.save()
        return self._instance

    @property
    def errors(self):
        return self._errors or {}

    @classmethod
    def separate_lookup_name(cls, field_name: str) -> tuple():

        """
        Separate lookup names.

        >> StorageHelper.separate_lookup_name('user__name')
        << ('user', 'name')

        >> StorageHelper.separate_lookup_name('name')
        << ('name', '')

        :return: tuple of str -> (first field name, lookup name)
        """
        field_name, _, lookup_name = field_name.partition(cls.LOOKUP_SEPARATOR)
        return field_name, lookup_name

    @classmethod
    def join_lookup_names(cls, *fields):
        return cls.LOOKUP_SEPARATOR.join(fields)

    @classmethod
    def get_field_from_lookup_name(cls, model_class, field_name: str) -> tuple():
        """
        Get model class and it's field from lookup string

        >> StorageHelper.get_field_from_lookup_name('contact__address__street_address')
        << (<class 'r3sourcer.apps.core.models.core.Address'>, 'street_address')

        :return: tuple ( model class object, field name )
        """
        if field_name.count(cls.LOOKUP_SEPARATOR):
            lookup_name, field_name = StorageHelper.separate_lookup_name(field_name)
            model_class = model_class._meta.get_field(lookup_name).related_model
            return cls.get_field_from_lookup_name(model_class, field_name)
        return model_class, field_name


class SimpleFieldHelper(object):
    """
    Helper class for flat fields (number, str, bool, etc.)
    """

    __slots__ = [
        'name', 'value'
    ]

    def __init__(self, name, value):
        assert re.match('^[a-z]+[\w_]*$', name, re.IGNORECASE), "Incorrect field name"

        self.name = name
        self.value = value


class RelatedFieldHelper(object):
    """
    Helper class for ForeignObject fields, would be used for storing and manipulation related object fields.
    """

    __slots__ = ['_model', 'name', '_lookup_name', 'value', 'simple_fields', 'related_fields', '_done', '_form']

    def __init__(self, model, name, value):

        assert re.match('^[a-z]+[\w_]*$', name, re.IGNORECASE), "Incorrect field name"

        self.name, self._lookup_name = StorageHelper.separate_lookup_name(name)
        self._model = model._meta.get_field(self.name).related_model
        self._form = None

        self.value = None
        self._done = False
        self.simple_fields = {}
        self.related_fields = {}

        self.process_field(value)

    def process_field(self, value):
        assert not self._done, "Field already processed"

        if StorageHelper.LOOKUP_SEPARATOR in self._lookup_name:
            related_field = RelatedFieldHelper(self._model, self._lookup_name, value)
            self.related_fields.setdefault(related_field.name, related_field)
        else:
            if '_id' not in self._lookup_name:
                self.simple_fields.setdefault(self._lookup_name, SimpleFieldHelper(self._lookup_name, value))
        self._done = True

    @classmethod
    def merge(cls, field1, field2):
        """
        Merge fields from different related field instances.
        Would be use for extending field1 from field2.

        :param field1: RelatedFieldHelper
        :param field2: RelatedFieldHelper
        """

        for field_name, value in field2.related_fields.items():
            if field_name in field1.related_fields:
                cls.merge(field1.related_fields[field_name], field2.related_fields[field_name])
            else:
                field1.related_fields.setdefault(field_name, field2.related_fields[field_name])

        for field_name, value in field2.simple_fields.items():
            field1.simple_fields.setdefault(field_name, value)

    def save_related(self, parent_name=None):
        """
        Create new instance from related fields and simple fields, bind its to self._model instance.
        :return: self._model instance
        """
        if self.value is not None:
            return

        related_fields = {}
        errors = {}
        if self.related_fields:
            for name, related_field in self.related_fields.items():
                try:
                    related_field.save_related(name)
                    related_fields[name] = related_field.value
                except ValidationError as e:
                    if hasattr(e, 'error_dict'):
                        errors.update(e.error_dict)
                    elif hasattr(e, 'message'):
                        errors[name] = [e.message]
                    else:
                        errors[name] = e.error_list

        data = dict(
            **{name: field.value for name, field in self.simple_fields.items()},
            **related_fields
        )
        model_form = self.get_modelform(data)

        if not model_form.is_valid():
            errors.update({
                '{}__{}'.format(parent_name, field_name) if field_name != '__all__' else 'non_field_errors': errors
                for field_name, errors in model_form.errors.items()
            })
            raise exceptions.ValidationError(errors)

        self.value = model_form.save()

    def get_modelform(self, data):
        meta_class = type('Meta', (object, ), {
            'model': self._model,
            'fields': [name for name, field in self.simple_fields.items()]
        })

        form = type('RelatedForm', (ModelForm, ), {
            'Meta': meta_class,
        })

        return form(data)
