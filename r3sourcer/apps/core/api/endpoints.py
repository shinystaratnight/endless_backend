import copy
from itertools import chain

from django_filters.rest_framework import DjangoFilterBackend
from drf_auto_endpoint.endpoints import Endpoint
from drf_auto_endpoint.utils import get_field_dict
from rest_framework import serializers

from r3sourcer.apps.core_adapter.constants import FIELD_RELATED, FIELD_STATIC
from r3sourcer.apps.core_adapter.factories import filter_factory
from r3sourcer.apps.core_adapter.utils import api_reverse


class ApiEndpoint(Endpoint):
    list_name = None
    list_label = None
    list_filter = None
    list_tabs = None
    list_buttons = None

    list_editable_filter = None
    list_editable_buttons = None

    ordering = None
    ordering_mapping = None
    context_actions = None

    highlight = None
    edit_disabled = False

    _metadata_fields = None

    def __init__(self, model=None, **kwargs):
        super(ApiEndpoint, self).__init__(model, **kwargs)
        viewset = self.get_viewset()
        viewset.filter_class = filter_factory(self)

        if viewset.filter_class:
            filter_backends = list(getattr(viewset, 'filter_backends', []))
            if DjangoFilterBackend not in filter_backends:
                filter_backends.append(DjangoFilterBackend)
            viewset.filter_backends = filter_backends

    def get_fieldsets(self):
        """
        Example:

        fieldsets = (
            ('receive_order_confirmation_sms', 'legacy_myob_card_number'),
            {
                'type': 'row',
                'name': 'Row',  # optional
                'fields': (...),
            },
            {
                'type': 'collapse',
                'name': 'Collapse',  # required
                'collapsed': True,  # optional
                'fields': ('field', {
                    'type': 'row',
                    'fields': (...),
                }),
            },
            {
                'type': 'button|submit|link|radio_group|checkbox_group|text',
                'field': 'field',
                'label': 'label',
                'action': 'action',  # for button type
                'link': 'link',  # for link type
            },
            {
                'type': 'related',  # custom related
                'field': 'field',
                'endpoint': '/api/endpoint',
                'label': 'label',
                'add': True|False,  # can add related (optional)
                'edit': True|False,  # can edit related (optional)
                'delete': True|False,  # can delete related (optional)
            }
        )
        """

        return self.fieldsets

    def get_metadata_fields(self, meta=True):
        serializer_class = self.get_serializer()

        if hasattr(serializer_class.Meta, 'fields'):
            meta_fields = copy.copy(serializer_class.Meta.fields)
        else:
            meta_fields = '__all__'

        if meta_fields == '__all__':
            meta_fields = self.get_fields_for_serializer()
        serializer = serializer_class()

        fields = chain(meta_fields, getattr(serializer_class, 'get_method_fields', lambda self: [])(serializer))
        result = self._get_metadata_fields_info(fields, [], serializer, meta=meta)

        return result

    def _get_metadata_fields_info(self, fields, result, serializer, meta=True):
        serializer_class = type(serializer)
        for field_name in fields:
            if field_name not in serializer.fields:
                continue

            field = serializer.fields[field_name]
            related_serializer = None
            if isinstance(field, serializers.ModelSerializer):
                related_serializer = field

            if related_serializer:
                related_fields = self._get_metadata_fields_info(
                    related_serializer.fields.keys(), [],
                    related_serializer, meta
                )
                if meta:
                    result.extend([
                        {**related_field, 'key': '{}.{}'.format(field_name, related_field['key'])}
                        for related_field in related_fields
                    ])
                else:
                    result.extend([
                        '{}.{}'.format(field_name, related_field)
                        for related_field in related_fields
                    ])

            if meta:
                field_dict = get_field_dict(field_name, serializer_class,
                                            model=serializer_class.Meta.model)
                if field_dict['type'] in ('tomany-table', 'manytomany-lists'):
                    field_dict['type'] = FIELD_RELATED
                    field_dict['many'] = True
                elif field_dict['type'] == 'foreignkey':
                    field_dict['type'] = FIELD_RELATED
                elif isinstance(field, serializers.SerializerMethodField):
                    field_dict['type'] = FIELD_STATIC

                result.append(field_dict)
            else:
                result.append(field_name)
        return result

    def get_list_name(self):
        if not self.list_name:
            return self.singular_model_name
        return self.list_name

    def get_list_label(self):
        if not self.list_label:
            return self.model._meta.verbose_name
        return self.list_label

    def get_ordering_fields(self):
        if self.ordering_fields is None:
            self.ordering_fields = set(self.get_metadata_fields(False))

        if self.ordering_mapping:
            self.ordering_fields = set(self.ordering_fields) | {
                val for val in self.ordering_mapping.values()
            }

        return self.ordering_fields

    def get_ordering(self):
        if self.ordering is None:
            self.ordering = []
        return self.ordering

    def get_ordering_mapping(self):
        if self.ordering_mapping is None:
            self.ordering_mapping = {}
        return self.ordering_mapping

    def get_context_actions(self):
        return self.context_actions

    def get_list_filter(self):
        if self.list_filter is None:
            self.list_filter = []
        return self.list_filter

    def get_list_tabs(self):
        if self.list_tabs is None:
            self.list_tabs = []
        return self.list_tabs

    def get_list_buttons(self):
        return self.list_buttons

    def get_bulk_actions(self):
        rv = []
        viewset = self.get_viewset()

        for action_name in dir(viewset):
            action = getattr(viewset, action_name)
            if getattr(action, 'action_type', None) == 'bulk':
                bulk_action = {
                    'url': api_reverse(self.get_url(), action.__name__.lower()),
                    'verb': action.bind_to_methods[0],
                }
                bulk_action.update(action.action_kwargs)
                rv.append(bulk_action)

        return rv

    def get_list_editable_filter(self):
        if self.list_editable_filter is None:
            self.list_editable_filter = []
        return self.list_editable_filter

    def get_list_editable_buttons(self):
        return self.list_editable_buttons
