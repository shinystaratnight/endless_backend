import re

from django.db import models
from django.db import transaction


__all__ = [
    'StorageHelper', 'SimpleFieldHelper', 'RelatedFieldHelper'
]


class StorageHelper(object):
    """
    Helper class for form builder.
    Would be use for creating new objects from FormStorage.
    """

    __slots__ = ['_model', '_fields', '_source_fields', '_done', '_instance']

    LOOKUP_SEPARATOR = '__'

    def __init__(self, model, fields: dict):
        assert issubclass(model, models.Model), "`model` should be models.Model subclass"

        self._model = model
        self._source_fields = fields
        self._fields = {}
        self._done = False
        self._instance = None

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

    @transaction.atomic
    def create_instance(self):
        """
        Create instance using fields (RelatedFields and SimpleFields)

        :return: self.model instance.
        """
        assert self._instance is None, 'Instance already created'

        object_params = {}
        for name, field in self._fields.items():
            if isinstance(field, RelatedFieldHelper):
                field.save_related()
            object_params.setdefault(name, field.value)
        self._instance = self._model.objects.create(**object_params)
        return self._instance

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

    __slots__ = ['_model', 'name', '_lookup_name', 'value', 'simple_fields', 'related_fields', '_done']

    def __init__(self, model, name, value):

        assert re.match('^[a-z]+[\w_]*$', name, re.IGNORECASE), "Incorrect field name"

        self.name, self._lookup_name = StorageHelper.separate_lookup_name(name)
        self._model = model._meta.get_field(self.name).related_model

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
                field1.related_fields[field_name].setdefault(field_name, field2.related_fields[field_name])

        for field_name, value in field2.simple_fields.items():
            field1.simple_fields.setdefault(field_name, value)

    def save_related(self):
        """
        Create new instance from related fields and simple fields, bind its to self._model instance.
        :return: self._model instance
        """
        if self.value is not None:
            return
        if self.related_fields:
            for name, related_field in self.related_fields.items():
                related_field.save_related()
        self.value = self._model(**{
            name: field.value
            for name, field in self.simple_fields.items()
        })
        self.value.save()
