from django_filters import (
    UUIDFilter, ChoiceFilter, DateFromToRangeFilter, DateTimeFromToRangeFilter
)
from django_filters.rest_framework import FilterSet
from django.utils.translation import ugettext_lazy as _

from . import constants
from .filters import ValuesFilter


def _get_field(fields, field_name):
    for field in fields:
        if field['key'] == field_name:
            return field
    return None


def filter_factory(endpoint):
    list_filters = endpoint.get_list_filter()
    meta_fields = endpoint.get_metadata_fields()

    attrs = {}

    if hasattr(endpoint, 'filter_class'):
        base_class = endpoint.filter_class
    else:
        base_class = FilterSet

    for list_filter in list_filters:
        if isinstance(list_filter, str):
            list_filter = {'field': list_filter}

        field = list_filter['field']

        if field in base_class.declared_filters:
            continue

        meta_field = _get_field(meta_fields, field)
        field_type = list_filter.get('type', meta_field['type'])
        field_qry = field.replace('.', '__')

        if field_type == constants.FIELD_RELATED:
            attrs[field_qry] = UUIDFilter(lookup_expr='id')
        elif field_type == constants.FIELD_SELECT:
            if 'choices' in list_filter:
                choices = list_filter['choices']
            elif 'choices' in meta_field:
                choices = meta_field['choices']
            else:
                continue  # pragma: no cover

            kwargs = {
                'name': field_qry,
                'empty_label': _('All'),
            }
            if list_filter.get('is_qs', False):
                choice_filter_class = ValuesFilter
            else:
                choice_filter_class = ChoiceFilter

                if not callable(choices):
                    choices = [(choice['value'], choice['label'])
                            for choice in choices]

                kwargs['choices'] = choices

            attrs[field_qry] = choice_filter_class(**kwargs)

        elif field_type in [constants.FIELD_DATE,
                            constants.FIELD_DATETIME]:
            is_date = field_type == constants.FIELD_DATE
            if is_date:
                field_class = DateFromToRangeFilter
            else:
                field_class = DateTimeFromToRangeFilter

            attrs[field_qry] = field_class(
                name=field_qry
            )
        else:
            continue  # pragma: no cover

    if not attrs:
        return base_class if base_class is not FilterSet else None

    base_meta_fields = getattr(base_class.Meta, 'fields', []) \
        if base_class is not FilterSet else []
    meta_fields = set(base_meta_fields)
    meta_fields.update(attrs.keys())

    cls_name = '{}Filter'.format(endpoint.model.__name__)

    attrs['Meta'] = type('Meta', (object, ), {
        'model': endpoint.model,
        'fields': meta_fields,
    })

    return type(cls_name, (base_class, ), attrs)