import re

from django.db import models
from django.db import transaction


class AlreadyProcessed(Exception):
    pass


class StorageHelper(object):

    __slots__ = ['model', 'fields', 'separator', '_fields']

    LOOKUP_SEPARATOR = '__'

    def __init__(self, model, fields: dict):
        assert issubclass(model, models.Model), "`model` should be models.Model subclass"

        self.model = model
        self._fields = fields
        self.fields = {}

    def process_fields(self):
        """
        
        :return: 
        """
        for field_name, field_value in self._fields.items():
            if self.LOOKUP_SEPARATOR in field_name:
                field = RelatedFieldHelper(self.model, field_name, field_value)
                if field.name in self.fields:
                    old_field = self.fields.get(field.name)
                    RelatedFieldHelper.merge(old_field, field)
                else:
                    self.fields.setdefault(field.name, field)
            else:
                self.fields.setdefault(field_name, SimpleFieldHelper(field_name, field_value))

    @transaction.atomic
    def create_instance(self):
        """
        Create instance using fields (RelatedFields and SimpleFields)

        :return: self.model instance.
        """
        object_params = {}
        for name, field in self.fields.items():
            if isinstance(field, RelatedFieldHelper):
                field.save_related()
            object_params.setdefault(name, field.value)
        return self.model.objects.create(**object_params)

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


class SimpleFieldHelper(object):

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

    __slots__ = ['model', 'name', 'lookup_name', 'value', 'simple_fields', 'related_fields', '_done']

    def __init__(self, model, name, value):

        assert re.match('^[a-z]+[\w_]*$', name, re.IGNORECASE), "Incorrect field name"

        self.name, self.lookup_name = StorageHelper.separate_lookup_name(name)
        self.model = model._meta.get_field(self.name).related_model

        self.value = None
        self._done = False
        self.simple_fields = {}
        self.related_fields = {}

        self.process_field(value)

    def process_field(self, value):
        assert not self._done, "Field already processed"

        if StorageHelper.LOOKUP_SEPARATOR in self.lookup_name:
            related_field = RelatedFieldHelper(self.model, self.lookup_name, value)
            self.related_fields.setdefault(related_field.name, related_field)
        else:
            self.simple_fields.setdefault(self.lookup_name, SimpleFieldHelper(self.lookup_name, value))
        self._done = True

    @classmethod
    def merge(cls, field1, field2):

        for k, v in field2.related_fields.items():
            if k in field1.related_fields:
                cls.merge(field1.related_fields[k], field2.related_fields[k])
            else:
                field1.related_fields[k].setdefault(k, field2.related_fields[k])

        for k, v in field2.simple_fields.items():
            field1.simple_fields.setdefault(k, field2.simple_fields[k])

    def save_related(self):
        if self.value is not None:
            return
        if self.related_fields:
            for name, related_field in self.related_fields.items():
                related_field.save_related()
        self.value = self.model(**{
            name: field.value
            for name, field in self.simple_fields.items()
        })
        self.value.save()
