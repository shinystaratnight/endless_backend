import six

from datetime import timedelta
from collections import OrderedDict

from django.urls.exceptions import NoReverseMatch
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from drf_auto_endpoint.adapters import (
    BaseAdapter, GETTER, PROPERTY, MetaDataInfo
)

from . import constants
from .utils import api_reverse


CUSTOM_FIELD_ATTRS = (
    'label', 'link', 'action', 'endpoint', 'add', 'edit', 'delete', 'read_only', 'label_upload', 'label_photo', 'many',
    'list', 'values', 'color', 'default', 'collapsed', 'file', 'photo', 'hide', 'prefilled', 'add_label', 'query',
    'showIf', 'send',
)


def format_str(val, *args, **kwargs):
    if isinstance(val, six.string_types):
        # Angular formatstring
        val = val.replace('{', '{' * 3).replace('}', '}' * 3)
        return val.format(*args, **kwargs)
    return val


def format_date(date):
    return date.strftime('%Y-%m-%d')


def to_html_tag(component_type):
    custom_types = [
        constants.FIELD_CHECKBOX, constants.FIELD_RADIO, constants.FIELD_TEXTAREA, constants.FIELD_SELECT,
        constants.FIELD_RADIO_GROUP, constants.FIELD_CHECKBOX_GROUP, constants.FIELD_BUTTON, constants.FIELD_LINK,
        constants.FIELD_SUBMIT, constants.FIELD_RELATED, constants.FIELD_STATIC, constants.FIELD_RULE,
        constants.FIELD_ICON, constants.FIELD_TIMELINE, constants.FIELD_LIST,
    ]
    if component_type in custom_types:
        return component_type
    elif component_type in [constants.FIELD_DATE, constants.FIELD_DATETIME]:
        return 'datepicker'
    return 'input'


class AngularApiAdapter(BaseAdapter):

    metadata_info = [
        MetaDataInfo('metadata_fields', GETTER, []),
        MetaDataInfo('fieldsets', GETTER, []),
    ]

    _excluded_field = {'updated_at', 'created_at', '__str__'}
    _hidden_fields = {'id'}
    edit = True

    def __init__(self, edit=True, * args, **kwargs):
        self.edit = edit

    @classmethod
    def adapt_field(cls, field):
        if 'type' not in field or field['type'] in constants.CONTAINER_TYPES:
            return field

        component_type = field.get('component_type', field['type'])
        if 'key' in field and '__str__' in field['key']:
            component_type = constants.FIELD_STATIC
        if component_type in constants.NON_FIELDS_TYPES:
            adapted = {
                'type': component_type,
                'templateOptions': {
                    'text': field.get('label', ''),
                    'label': field.get('label', ''),
                    'type': component_type,
                }
            }
            if 'key' in field:
                adapted['key'] = field['key']
            if component_type == constants.FIELD_TIMELINE:
                adapted['endpoint'] = field.get('endpoint')
                adapted['key'] = constants.FIELD_TIMELINE
            elif component_type == constants.FIELD_LINK:
                adapted['templateOptions']['link'] = field.get('link')
            elif component_type == constants.FIELD_LIST:
                adapted.update(
                    collapsed=field.get('collapsed', False),
                    **{attr: field[attr] for attr in ('endpoint', 'prefilled')
                       if field.get(attr) is not None}
                )
                if field.get('add_label'):
                    adapted['templateOptions']['add_label'] = field['add_label']
            elif component_type != constants.FIELD_SUBMIT:
                adapted['templateOptions']['action'] = field['action']

            query_params = field.get('query')
            if query_params is not None:
                adapted['query'] = query_params

            if 'showIf' in field:
                adapted['showIf'] = field['showIf']

            return adapted
        elif component_type == constants.FIELD_RELATED:
            if 'related_endpoint' in field:
                try:
                    endpoint = api_reverse(
                        field['related_endpoint'].replace('_', '-')
                    )
                except NoReverseMatch:
                    return {'key': field['key']}
            else:
                endpoint = field['endpoint']
            adapted = {
                'type': component_type,
                'endpoint': endpoint,
                'many': field.get('many', False),
                'list': field.get('list', False),
                'collapsed': field.get('collapsed', False),
                'templateOptions': {
                    'delete': field.get('delete', False),
                    **{attr: field.get(attr, True) for attr in ('add', 'edit')}
                }
            }
        elif component_type == constants.FIELD_ICON:
            default_icons = {
                True: 'check-circle',
                False: 'times-circle',
                None: 'minus-circle',
            }

            icons = field.get('values', {})

            for key, icon in default_icons.items():
                if key not in icons:
                    icons[key] = icon

            field['validation']['values'] = icons

            adapted = {
                'type': constants.FIELD_CHECKBOX,
                'templateOptions': field['validation'],
            }
        else:
            adapted = {
                'type': to_html_tag(component_type),
                'templateOptions': field['validation'],
            }

        adapted['read_only'] = field.get('read_only', False)
        adapted['key'] = field.get('key')
        if ('default' in field and
                isinstance(field['default'], (str, int, float, bool))):
            adapted['default'] = field['default']

        if 'showIf' in field:
            adapted['showIf'] = field['showIf']

        if 'send' in field:
            adapted['send'] = field['send']

        field_ui = field.get('ui', {})
        ui_options = ('placeholder', 'label_upload', 'label_photo', 'color', 'file', 'photo')
        adapted['templateOptions'].update({
            'type': component_type,
            'label': field.get('label', field_ui.get('label', '')),
            **{
                option: field_ui[option] for option in ui_options
                if field_ui.get(option) is not None
            },
            **{
                option: field[option] for option in ui_options
                if field.get(option) is not None
            },
        })

        is_hidden = field.get('hide')
        if field['key'].split('.')[-1] in cls._hidden_fields or is_hidden:
            adapted['hide'] = True

        if field_ui.get('help'):
            adapted['templateOptions']['description'] = field_ui['help']

        if 'choices' in field:
            for choice in field['choices']:
                if isinstance(choice['value'], timedelta):
                    choice['value'] = int(choice['value'].total_seconds())

            adapted['templateOptions']['options'] = field['choices']

        return adapted

    def _map_fieldsets(self, fieldsets, fields):
        if self.edit:
            fields = [
                field for field in fields
                if field['key'].split('.')[-1] not in self._excluded_field
            ]
        if not fieldsets:
            return [self.adapt_field(field) for field in fields]
        return self._get_metadata_fieldsets_info(fieldsets, [], fields)

    def _get_metadata_fieldsets_info(self, fieldsets, result, fields):
        for fieldset in fieldsets:
            if isinstance(fieldset, dict):
                field_info = self._process_dict_fieldset(fieldset, fields)
            elif isinstance(fieldset, (list, tuple)):
                field_info = self._get_metadata_fieldsets_info(
                    fieldset, [], fields
                )
            else:
                field_info = self._get_field_info(fieldset, fields)

            if isinstance(field_info, (list, tuple)):
                result.extend(field_info)
            elif field_info is not None:
                result.append(field_info)

        return result

    def _process_dict_fieldset(self, fieldset, fields):
        fieldset_type = fieldset.get('type')
        if fieldset_type is not None and fieldset_type not in constants.CONTAINER_TYPES:
            field_info = self._get_field_info(
                fieldset.get('field'), fields, fieldset_type, fieldset
            )
            return field_info

        fildset_result = self._get_metadata_fieldsets_info(
            fieldset['fields'], [], fields
        )
        if fieldset_type is None:
            return fildset_result
        else:
            field_info = {
                'type': fieldset_type,
                'children': fildset_result,
                **{
                    key: fieldset[key] for key in ('name', 'collapsed')
                    if fieldset.get(key)
                },
            }
            return field_info

    def _get_field_info(self, field_name, fields, component_type=None,
                        fieldset=None):
        data = None
        for field in fields:
            key = field.get('key')
            if field_name == key:
                return self._adapt_fieldset(field, fieldset, component_type)

        if data is None and component_type in constants.NON_FIELDS_TYPES:
            data = self._adapt_fieldset(
                {'type': component_type}, fieldset, component_type
            )
        return data

    def _adapt_fieldset(self, field, fieldset=None, component_type=None):
        field['component_type'] = component_type or field['type']
        if fieldset:
            field.update(
                {attr: fieldset[attr] for attr in CUSTOM_FIELD_ATTRS
                 if fieldset.get(attr) is not None}
            )
        data = self.adapt_field(field)
        return data

    def render(self, config):
        fields = config['metadata_fields']
        fieldsets = config['fieldsets']

        adapted = self._map_fieldsets(fieldsets, fields)

        return adapted


class AngularListApiAdapter(AngularApiAdapter):
    adapted_fields = None
    fields = None
    list_editable = None
    is_formset = False

    metadata_info = [
        MetaDataInfo('metadata_fields', GETTER, []),
        MetaDataInfo('list_display', GETTER, []),
        MetaDataInfo('list_editable', GETTER, []),
        MetaDataInfo('list_name', GETTER, []),
        MetaDataInfo('list_label', GETTER, []),
        MetaDataInfo('list_filter', GETTER, {}),
        MetaDataInfo('search_enabled', PROPERTY, []),
        MetaDataInfo('ordering_fields', GETTER, []),
        MetaDataInfo('ordering_mapping', GETTER, []),
        MetaDataInfo('ordering', GETTER, []),
        MetaDataInfo('context_actions', GETTER, {}),
        MetaDataInfo('highlight', PROPERTY, {}),
        MetaDataInfo('bulk_actions', GETTER, []),
        MetaDataInfo('list_tabs', GETTER, []),
        MetaDataInfo('list_buttons', GETTER, []),
        MetaDataInfo('list_editable_filter', GETTER, []),
    ]

    def __init__(self, *args, **kwargs):
        self.adapted_fields = {}
        self.fields = []
        self.list_editable = []
        self.is_formset = kwargs.pop('is_formset', False)

        super(AngularListApiAdapter, self).__init__(*args, **kwargs)

    def _adapt_field(self, display_field_name, fields=None,
                     list_editable=None, field_type=None):
        display_field = None
        list_editable = list_editable or self.list_editable
        fields = fields or self.fields

        if isinstance(display_field_name, dict):
            field_dict = display_field_name
            display_field_name = field_dict.get('field')
        else:
            field_dict = {}

        field = self._get_field(fields, display_field_name)

        if field:
            field.update(field_dict)
            if field_type:
                field['type'] = field_type
            display_field = self.adapt_field(field)
            if not self.is_formset:
                display_field['read_only'] = display_field_name not in list_editable

        if display_field:
            return display_field
        return None

    def _adapt_filters(self, list_filters):
        adapted_filters = []
        for list_filter in list_filters:
            if isinstance(list_filter, str):
                list_filter = {'field': list_filter}

            field = list_filter['field']
            meta_field = self._get_field(self.fields, field)
            field_type = list_filter.get('type', meta_field['type'])
            field_qry = field.replace('.', '__')

            label = list_filter.get('label', meta_field.get('label'))
            if not label:
                field_ui = meta_field.get('ui', {})
                label = field_ui.get('label', '')

            adapted = {
                'type': field_type,
                'key': field,
                'label': label,
            }

            if field_type == constants.FIELD_RELATED:
                if 'endpoint' in list_filter:
                    endpoint = list_filter['endpoint']
                elif 'related_endpoint' in meta_field:
                    try:
                        endpoint = api_reverse(
                            meta_field['related_endpoint'].replace('_', '-')
                        )
                    except NoReverseMatch:
                        continue
                else:
                    endpoint = meta_field.get('endpoint')

                adapted.update({
                    'query': field_qry,
                    'data': {
                        'endpoint': endpoint,
                        'key': list_filter.get('key', 'id'),
                        'value': list_filter.get('value', '__str__'),
                    }
                })
            elif field_type == constants.FIELD_SELECT:
                if 'choices' in list_filter:
                    choices = list_filter['choices']
                elif 'choices' in meta_field:
                    choices = list(meta_field['choices'])
                else:
                    continue  # pragma: no cover

                if not choices:
                    continue

                if callable(choices):
                    choices = choices()

                choices = [{
                    'label': _('All'),
                    'value': '',
                }] + list(choices)

                adapted.update({
                    'query': field_qry,
                    'options': choices,
                })
            elif field_type in [constants.FIELD_DATE,
                                constants.FIELD_DATETIME]:
                from_qry = '%s_0' % field_qry
                to_qry = '%s_1' % field_qry

                adapted.update({
                    'input': [{
                        'query': from_qry,
                        'label': _('From date'),
                    }, {
                        'query': to_qry,
                        'label': _('To date'),
                    }]
                })

                action_list = list_filter.get('actions')
                if action_list is None:
                    today = timezone.now().date()
                    action_list = [{
                        'label': _('Yesterday'),
                        'query': '%s=%s' % (from_qry, format_date(
                            today - timedelta(days=1)
                        ))
                    }, {
                        'label': _('Today'),
                        'query': '%(from)s=%(datetime)s&%(to)s=%(datetime)s' % {
                            'from': from_qry,
                            'to': to_qry,
                            'datetime': format_date(today),
                        }
                    }, {
                        'label': _('Tomorrow'),
                        'query': '%s=%s' % (from_qry, format_date(
                            today + timedelta(days=1)
                        ))
                    }]

                adapted['list'] = action_list
            else:
                continue  # pragma: no cover

            adapted_filters.append(adapted)
        return adapted_filters

    def _adapt_actions(self, bulk_actions):
        adapted_list = []

        for bulk_action in bulk_actions:
            adapted = {
                'label': bulk_action['text'],
                'endpoint': bulk_action['url'],
                'confirm': bulk_action.get('confirm', True),
                'message': bulk_action.get('message', _('Are you sure?')),
            }
            adapted_list.append(adapted)

        return {
            'label': _('Actions'),
            'button_label': _('Go'),
            'agree_label': _('Agree'),
            'decline_label': _('Decline'),
            'options': adapted_list,
        }

    def _get_field(self, fields, field_name):
        for field in fields:
            if field['key'] == field_name:
                return field
        return None

    def get_adapted_field(self, field_name, field_type=None):
        field_dict = field_name

        if isinstance(field_name, dict):
            field_name = field_name.get('field')

        if (field_name not in self.adapted_fields or
                self.adapted_fields[field_name]['templateOptions']['type'] != field_type):
            self.adapted_fields[field_name] = self._adapt_field(
                field_dict, field_type=field_type
            )
        return self.adapted_fields[field_name]

    def adapt_list_display(self, display_fields, list_filters, bulk_actions):
        adapted_columns = self._adapt_columns(display_fields)
        list_dict = {
            'columns': adapted_columns,
        }
        if list_filters:
            adapted_filters = self._adapt_filters(list_filters)
            list_dict['filters'] = adapted_filters
        if bulk_actions:
            adapted_actions = self._adapt_actions(bulk_actions)
            list_dict['actions'] = adapted_actions
        return list_dict

    def _adapt_columns(self, display_fields):
        adapted_columns = []

        for display_field in display_fields:
            name = label = ''
            if isinstance(display_field, (list, tuple)):
                if len(display_field) != 2:
                    raise ValueError('Composite content should have 2 items')
                elif not isinstance(display_field[1], (list, tuple)):
                    raise ValueError('Second element should be list or '
                                     'tuple of fields in composite content')

                name = display_field[0].replace(' ', '_').lower()
                label = display_field[0]
                display_field_list = display_field[1]
            elif isinstance(display_field, dict):
                label, name, display_field_list = self._process_dict_field(
                    display_field
                )
            else:
                display_field_list = [display_field]

            if not name or not label:
                field = self.get_adapted_field(display_field_list[0])
                name = field['key']
                label = field['templateOptions']['label']

            content = self._adapt_column_fields(display_field_list)
            adapted_columns.append({
                'name': name,
                'label': label,
                'content': content,
            })

        return adapted_columns

    def _process_dict_field(self, display_field):
        field = display_field.get('field')
        label = display_field.get('label', '')
        name = display_field.get(
            'name', label.replace(' ', '_').lower()
        )
        if field is None:
            if not label:
                raise ValueError(
                    "Composite content dict should have 'label' key"
                )
            display_field_list = display_field.get('fields')
        else:
            display_field_list = [display_field]

        return label, name, display_field_list

    def _adapt_column_fields(self, display_fields):
        adapted = []
        options = ('endpoint', 'link', 'values', 'action', 'label', 'text',
                   'icon', 'repeat', 'color', 'visible', 'hidden',
                   'replace_by')

        for display_field in display_fields:
            if isinstance(display_field, dict):
                field = display_field.get('field')
                fields = display_field.get('fields')
                field_type = display_field.get('type')

                if field:
                    display_field_attrs = display_field
                elif fields:
                    if not field_type:
                        raise ValueError("Extended field with 'fields' param "
                                         "should have 'type'")

                    adapted_result = self._adapt_column_fields(fields)

                    adapted.append({
                        'type': field_type,
                        'fields': adapted_result,
                        **{o: display_field[o] for o in options if display_field.get(o)}
                    })

                    continue
                else:
                    raise ValueError("'field' or 'fields' value should be set "
                                     "in extended field")
            else:
                field = display_field
                field_type = None
                display_field_attrs = {}

            adapted_field = self.get_adapted_field(
                display_field, field_type=field_type
            )
            field_type = field_type or adapted_field.get('type',
                                                         constants.FIELD_STATIC)

            adapt_field = {
                'type': field_type,
                'field': field,
                **{o: format_str(display_field_attrs[o], field=field)
                    for o in options
                    if display_field_attrs.get(o)},
                **{o: format_str(adapted_field[o], field=field)
                    for o in options
                    if o not in display_field_attrs and adapted_field.get(o)}
            }

            if field_type == constants.FIELD_SELECT:
                values = adapted_field['templateOptions'].get('options')
                if values and not adapt_field.get('values'):
                    adapt_field['values'] = OrderedDict(
                        [(item['value'], item['label']) for item in values]
                    )

            adapted.append(adapt_field)

        return adapted

    def adapt_ordering(self, display_fields, ordering_fields, ordering_mapping,
                       ordering):
        columns = display_fields['columns']

        for column in columns:
            sorting_field = ordering_mapping.get(column['name'])
            sort = sorting_field is not None

            if sorting_field is None and len(column['content']) == 1:
                field = column['content'][0].get('field')
                sorting_field = column['name']
                sort = (
                    field in self.adapted_fields and
                    self.adapted_fields[field]['type'] != constants.FIELD_STATIC and
                    sorting_field in ordering_fields
                )

            if sort:
                column['sort'] = True
                column['sort_field'] = sorting_field
                for order in ordering:
                    if column['name'] == order.strip('-'):
                        column['sorted'] = 'desc' if order[0] == '-' else 'asc'

        return columns

    def adapt_context_menu(self, display_fields, context_actions):
        columns = display_fields['columns']

        for column in columns:
            if column['name'] in context_actions:
                column['context_menu'] = context_actions[column['name']]

        return columns

    def adapt_highlight(self, highlight):
        field_name = highlight.get('field')
        field = self._get_field(self.fields, field_name)
        if not field:
            return

        adapted = {
            'field': field_name,
        }

        if field['type'] != constants.FIELD_CHECKBOX and (
            field['type'] != constants.FIELD_SELECT or
            'choices' not in field
        ):
            return

        adapted['values'] = {key: True for key in highlight.get('values', [])}

        return adapted

    def adapt_tabs(self, list_tabs):
        res_tabs = []

        for tab in list_tabs:
            if isinstance(tab, (tuple, list)):
                label = ''
                fields = tab
                is_colapsed = True
            elif isinstance(tab, dict):
                fields = tab['fields']
                label = tab.get('label')
                is_colapsed = tab.get('is_collapsed', True)
            else:
                fields = []

            if len(fields) == 0:
                continue

            if not label:
                field = self._get_field(self.fields, fields[0])
                label = field['ui']['label']

            res_tabs.append({
                'label': label,
                'fields': fields,
                'is_collapsed': is_colapsed
            })

        return res_tabs

    def adapt_buttons(self, list_buttons):
        res_buttons = []

        for button in list_buttons:
            if not isinstance(button, dict):
                continue

            res_buttons.append(button)

        return res_buttons

    def render(self, config):  # pragma: no cover
        self.fields = config['metadata_fields']
        self.list_editable = config['list_editable']
        if self.is_formset and self.list_editable:
            display_fields = self.list_editable
        else:
            self.list_editable = []
            display_fields = config['list_display']

        list_editable_filter = config['list_editable_filter']
        if self.is_formset:
            list_filters = list_editable_filter or []
        else:
            list_filters = config['list_filter']

        ordering_fields = config['ordering_fields']
        ordering_mapping = config['ordering_mapping']
        ordering = config['ordering']
        context_actions = config['context_actions'] or {}
        highlight = config['highlight']
        bulk_actions = config['bulk_actions']
        list_tabs = config['list_tabs']
        list_buttons = config['list_buttons']

        display_fields = self.adapt_list_display(
            display_fields, list_filters, bulk_actions
        )
        display_fields.update(
            list=config['list_name'],
            label=config['list_label'],
            search_enabled=config['search_enabled']
        )
        display_fields['columns'] = self.adapt_ordering(
            display_fields, ordering_fields, ordering_mapping, ordering
        )
        display_fields['columns'] = self.adapt_context_menu(
            display_fields, context_actions
        )
        if highlight:
            display_fields['highlight'] = self.adapt_highlight(highlight)

        if list_tabs:
            display_fields['tabs'] = self.adapt_tabs(list_tabs)

        if list_buttons is not None:
            display_fields['buttons'] = self.adapt_buttons(list_buttons)

        return {
            'fields': self.adapted_fields.values(),
            'list': display_fields,
        }
