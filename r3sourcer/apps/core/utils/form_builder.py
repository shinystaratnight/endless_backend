import re

from django.db import models
from django.db import transaction


class StorageHelper(object):

    __slots__ = ['model', 'fields', 'separator', '_fields']

    def __init__(self, model, fields: dict, separator: str ='__'):
        self.model = model
        self.separator = separator
        self._fields = fields
        self.fields = {}

    def process_fields(self):
        for field_name, field_value in self._fields.items():
            if '__' in field_name:
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
        object_params = {}
        for name, field in self.fields.items():
            if isinstance(field, RelatedFieldHelper):
                field.save_related()
            object_params.setdefault(name, field.value)
        return self.model.objects.create(**object_params)


class SimpleFieldHelper(object):

    __slots__ = [
        'name', 'value'
    ]

    def __init__(self, name, value):
        assert re.match('$\w+[\w\d_]*^', name), "Incorrect field name"

        self.name = name
        self.value = value


class RelatedFieldHelper(object):

    __slots__ = ['model', 'name', 'lookup_name', 'value', 'simple_fields', 'related_fields']

    def __init__(self, model, name, value):

        assert re.match('$\w+[\w\d_]*^', name), "Incorrect field name"

        self.name, _, self.lookup_name = name.partition('__')
        self.model = model._meta.get_field(self.name).related_model

        self.value = None
        self.simple_fields = {}
        self.related_fields = {}

        self.process_field(value)

    def process_field(self, value):
        if '__' in self.lookup_name:
            related_field = RelatedFieldHelper(self.model, self.lookup_name, value)
            self.related_fields.setdefault(related_field.name, related_field)
        else:
            self.simple_fields.setdefault(self.lookup_name, SimpleFieldHelper(self.lookup_name, value))

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
