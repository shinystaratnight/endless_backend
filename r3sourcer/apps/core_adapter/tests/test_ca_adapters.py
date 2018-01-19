import copy
import mock
import pytest

from datetime import date, timedelta

from django.urls.exceptions import NoReverseMatch
from freezegun import freeze_time

from r3sourcer.apps.core_adapter.adapters import (
    to_html_tag, format_str, format_date, AngularApiAdapter,
    AngularListApiAdapter
)
from r3sourcer.apps.core_adapter.constants import (
    CONTAINER_TYPES, CONTAINER_ROW, CONTAINER_COLLAPSE, FIELD_RADIO_GROUP,
    FIELD_BUTTON, FIELD_RELATED, FIELD_SELECT, FIELD_TIMELINE, FIELD_LIST
)


class TestFunctions:

    @pytest.mark.parametrize(
        ['widget_type', 'expected'],
        [('checkbox', 'checkbox'), ('radio', 'radio'), ('select', 'select'),
         ('textarea', 'textarea'), ('date', 'datepicker'), ('email', 'input'),
         ('datetime', 'datepicker'), ('text', 'input'), ('number', 'input')]
    )
    def test_to_html_tag_special_input(self, widget_type, expected):
        widget_type = to_html_tag(widget_type)

        assert widget_type == expected

    def test_format_str_without_data(self):
        with pytest.raises(KeyError):
            format_str('{test}')

    def test_format_str_with_data(self):
        res = format_str('{test}', test='var')

        assert res == '{var}'

    def test_format_str_non_str_type(self):
        res = format_str(1)

        assert res == 1

    def test_format_str_non_str_type_with_data(self):
        res = format_str(1)

        assert res == 1

    @freeze_time(date(2017, 2, 1))
    def test_format_date(self):
        res = format_date(date.today())

        assert res == '2017-02-01'

    def test_format_date_non_date(self):
        with pytest.raises(AttributeError):
            format_date(1)


class TestAngularApiAdapter:

    def get_field(self, key='field'):
        return {
            'key': key,
            'type': 'text',
            'component_type': 'text',
            'read_only': False,
            'ui': {
                'label': 'Label',
                'placeholder': 'placeholder',
                'help': 'help',
            },
            'validation': {
                'required': True,
            },
            'extra': {},
            'translated': False
        }

    def get_button_field(self, key='field_button'):
        return {
            'key': key,
            'type': FIELD_BUTTON,
            'component_type': FIELD_BUTTON,
            'label': 'test',
            'action': 'action',
            'link': 'link',
        }

    def get_res_list(self, first_key='field', second_key='field2'):
        return [
            {
                'type': 'input',
                'key': first_key,
            },
            {
                'type': 'input',
                'key': second_key,
            },
            None,
        ]

    @pytest.fixture
    def field(self):
        return self.get_field()

    @pytest.fixture
    def second_field(self):
        return self.get_field('field2')

    @pytest.mark.parametrize(
        ['widget_type'],
        [(t,) for t in CONTAINER_TYPES]
    )
    def test_adapt_field_container_types(self, widget_type):
        res = AngularApiAdapter.adapt_field({
            'type': widget_type,
            'children': [],
        })

        assert 'children' in res

    def test_adapt_field_input_types(self):
        field = self.get_field()

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == 'input'
        assert 'templateOptions' in res
        for option in ('label', 'placeholder'):
            assert res['templateOptions'][option] == field['ui'][option]
        assert res['templateOptions']['description'] == field['ui']['help']

    def test_adapt_field_input_types_with_default(self):
        field = self.get_field()
        field['default'] = 'default'

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == 'input'
        assert res['default'] == 'default'

    def test_adapt_field_without_description(self):
        field = self.get_field()
        del field['ui']['help']

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == 'input'
        assert 'templateOptions' in res
        for option in ('label', 'placeholder'):
            assert res['templateOptions'][option] == field['ui'][option]
        assert 'description' not in res['templateOptions']

    def test_adapt_field_choices_type(self):
        field = self.get_field()
        field.update(
            choices=[{
                'label': 'Test',
                'value': 'test'
            }],
            type='select',
            component_type='select',
        )

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == 'select'
        assert 'templateOptions' in res
        assert res['templateOptions']['options'] == field['choices']
        for option in ('label', 'placeholder'):
            assert res['templateOptions'][option] == field['ui'][option]
        assert res['templateOptions']['description'] == field['ui']['help']

    def test_adapt_field_choices_timedelta_type(self):
        field = self.get_field()
        field.update(
            choices=[{
                'label': 'Test',
                'value': timedelta(seconds=60),
            }],
            type='select',
            component_type='select',
        )

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == 'select'
        assert 'templateOptions' in res
        assert res['templateOptions']['options'] == field['choices']
        for option in ('label', 'placeholder'):
            assert res['templateOptions'][option] == field['ui'][option]
        assert res['templateOptions']['description'] == field['ui']['help']

    @mock.patch('r3sourcer.apps.core_adapter.adapters.api_reverse')
    def test_adapt_field_related_type(self, mock_reverse):
        mock_reverse.return_value = '/api/v2/test/related/'

        field = self.get_field()
        field.update(
            related_endpoint='test/related',
            type=FIELD_RELATED,
            component_type=FIELD_RELATED,
        )

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == FIELD_RELATED
        assert 'templateOptions' in res
        assert field['related_endpoint'] in res['endpoint']

    @mock.patch('r3sourcer.apps.core_adapter.adapters.api_reverse')
    def test_adapt_field_related_endpoint_not_found(self, mock_reverse):
        mock_reverse.side_effect = NoReverseMatch

        field = self.get_field()
        field.update(
            related_endpoint='test/related',
            type=FIELD_RELATED,
            component_type=FIELD_RELATED,
        )

        res = AngularApiAdapter.adapt_field(field)

        assert 'type' not in res
        assert 'endpoint' not in res

    def test_adapt_field_custom_related_type(self):
        field = self.get_field()
        field.update(
            endpoint='test/related',
            type='related',
            component_type='related',
        )

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == 'related'
        assert 'templateOptions' in res
        assert res['templateOptions']['add']

    def test_adapt_field_button_type(self):
        field = self.get_button_field()

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == FIELD_BUTTON
        assert 'templateOptions' in res
        assert 'action' in res['templateOptions']

    def test_adapt_field_submit_type(self):
        field = self.get_button_field()
        field.update(type='submit', component_type='submit')

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == 'submit'
        assert 'templateOptions' in res
        assert 'action' not in res['templateOptions']

    def test_adapt_field_link_type(self):
        field = self.get_button_field()
        field.update(type='link', component_type='link')

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == 'link'
        assert 'templateOptions' in res
        assert 'link' in res['templateOptions']

    def test_adapt_field_static_type(self):
        field = self.get_field('__str__')

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == 'static'

    def test_adapt_field_icon_type(self):
        field = self.get_field()
        field.update(
            type='icon',
            component_type='icon',
        )

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == 'checkbox'
        assert 'templateOptions' in res
        assert res['templateOptions']['type'] == 'icon'

    def test_adapt_field_icon_type_custom_values(self):
        field = self.get_field()
        field.update(
            type='icon',
            component_type='icon',
            values={
                True: 'test',
            }
        )

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == 'checkbox'
        assert 'templateOptions' in res
        assert res['templateOptions']['values'][True] == 'test'

    def test_adapt_field_timeline_type(self):
        field = {
            'type': FIELD_TIMELINE,
            'label': 'label',
            'field': 'id',
            'endpoint': '/timeline/',
            'query': {
                'model': 'model',
                'object_id': '{id}',
            }
        }

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == FIELD_TIMELINE
        assert 'query' in res
        assert 'model' in res['query']
        assert 'object_id' in res['query']

    def test_adapt_field_list_type(self):
        field = {
            'type': FIELD_LIST,
            'label': 'label',
            'field': 'id',
            'endpoint': '/list/',
            'query': {
                'model': 'model',
                'object_id': '{id}',
            },
            'add_label': 'label'
        }

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == FIELD_LIST
        assert 'query' in res
        assert 'model' in res['query']
        assert 'add_label' in res['templateOptions']

    def test_adapt_field_list_type_without_add_button(self):
        field = {
            'type': FIELD_LIST,
            'label': 'label',
            'field': 'id',
            'endpoint': '/list/',
            'query': {
                'model': 'model',
                'object_id': '{id}',
            }
        }

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == FIELD_LIST
        assert 'query' in res
        assert 'model' in res['query']

    def test_adapt_field_hide_field(self):
        field = self.get_field('id')
        field['hide'] = True

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == 'input'
        assert res['hide']

    def test_adapt_field_input_showif(self):
        field = self.get_field()
        field['showIf'] = ['test']

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == 'input'
        assert 'showIf' in res

    def test_adapt_field_input_send(self):
        field = self.get_field()
        field['send'] = False

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == 'input'
        assert 'send' in res

    def test_adapt_field_button_type_showif(self):
        field = self.get_button_field()
        field['showIf'] = ['test']

        res = AngularApiAdapter.adapt_field(field)

        assert res['type'] == FIELD_BUTTON
        assert 'showIf' in res

    @mock.patch.object(AngularApiAdapter, '_get_metadata_fieldsets_info')
    def test_map_fieldsets(self, mock_get_metadata_fieldsets, field, second_field):
        mock_get_metadata_fieldsets.return_value = self.get_res_list()[:2]

        fieldsets = ('field', 'field2', )
        res = AngularApiAdapter()._map_fieldsets(fieldsets,
                                                 [field, second_field])

        assert len(res) == 2
        assert res[0]['key'] == field['key']
        assert res[1]['key'] == second_field['key']

    @mock.patch.object(AngularApiAdapter, '_get_metadata_fieldsets_info')
    def test_map_fieldsets_no_edit(self, mock_get_metadata_fieldsets, field,
                                   second_field):
        mock_get_metadata_fieldsets.return_value = self.get_res_list()[:2]

        fieldsets = ('field', 'field2', )
        res = AngularApiAdapter(edit=False)._map_fieldsets(
            fieldsets, [field, second_field]
        )

        assert len(res) == 2
        assert res[0]['key'] == field['key']
        assert res[1]['key'] == second_field['key']

    @mock.patch.object(AngularApiAdapter, 'adapt_field')
    def test_map_empty_fieldsets(self, mock_adapt_field, field, second_field):
        mock_adapt_field.side_effect = self.get_res_list()[:2]

        res = AngularApiAdapter()._map_fieldsets([], [field, second_field])

        assert len(res) == 2
        assert res[0]['key'] == field['key']
        assert res[1]['key'] == second_field['key']

    @mock.patch.object(AngularApiAdapter, 'adapt_field')
    def test_adapt_fieldset(self, mock_adapt_field, field):
        mock_adapt_field.return_value = {
            'type': 'input',
            'key': 'field'
        }

        res = AngularApiAdapter()._adapt_fieldset(field)

        assert res['key'] == field['key']

    @mock.patch.object(AngularApiAdapter, 'adapt_field')
    def test_adapt_fieldset_with_fieldset(self, mock_adapt_field):
        mock_adapt_field.return_value = {
            'type': FIELD_BUTTON,
            'templateOptions': {
                'label': 'label',
                'action': 'test',
            }
        }

        res = AngularApiAdapter()._adapt_fieldset(
            self.get_button_field(),
            {
                'type': FIELD_BUTTON,
                'action': 'test'
            }
        )

        assert res['type'] == FIELD_BUTTON
        assert res['templateOptions']['action'] == 'test'

    @mock.patch.object(AngularApiAdapter, 'adapt_field')
    def test_adapt_fieldset_with_fieldset_query(self, mock_adapt_field):
        mock_adapt_field.return_value = {
            'type': FIELD_TIMELINE,
            'label': 'label',
            'field': 'id',
            'endpoint': '/timeline/',
            'query': ['model', 'object_id'],
            'model': 'model',
            'object_id': '{id}',
        }

        res = AngularApiAdapter()._adapt_fieldset(
            self.get_field(),
            {
                'type': FIELD_TIMELINE,
                'label': 'label',
                'field': 'id',
                'endpoint': '/timeline/',
                'query': ['model', 'object_id'],
                'model': 'model',
                'object_id': '{id}',
            }
        )

        assert res['type'] == FIELD_TIMELINE
        assert 'query' in res

    @mock.patch.object(AngularApiAdapter, '_adapt_fieldset')
    def test_get_field_info_button_type(self, mock_adapt_field, field, second_field):
        mock_adapt_field.return_value = {
            'type': FIELD_BUTTON,
            'templateOptions': {
                'label': 'label',
                'action': 'test',
            }
        }

        res = AngularApiAdapter()._get_field_info(
            None,
            [field, second_field],
            FIELD_BUTTON,
            {
                'type': FIELD_BUTTON,
                'action': 'test'
            })

        assert res['type'] == FIELD_BUTTON

    @mock.patch.object(AngularApiAdapter, '_adapt_fieldset')
    def test_get_field_info(self, mock_adapt_field, field, second_field):
        mock_adapt_field.return_value = {
            'type': 'input',
            'key': 'field'
        }

        res = AngularApiAdapter()._get_field_info('field',
                                                  [field, second_field])

        assert res['key'] == field['key']

    def test_get_field_info_returns_none(self):
        field = self.get_field()
        res = AngularApiAdapter()._get_field_info('not_existing_field',
                                                  [field])

        assert res is None

    @mock.patch.object(AngularApiAdapter, '_map_fieldsets')
    def test_render_with_fieldsets(self, mock_map_fieldsets, field,
                                   second_field):
        mock_map_fieldsets.return_value = self.get_res_list(
            'field2', 'field'
        )[:2]

        res = AngularApiAdapter().render({
            'fieldsets': ('field2', 'field'),
            'metadata_fields': [field, second_field]
        })

        assert len(res) == 2
        assert res[0]['key'] == second_field['key']
        assert res[1]['key'] == field['key']

    @mock.patch.object(AngularApiAdapter, '_map_fieldsets')
    def test_render_without_fieldsets(self, mock_map_fieldsets, field,
                                      second_field):
        mock_map_fieldsets.return_value = self.get_res_list()[:2]

        res = AngularApiAdapter().render({
            'fieldsets': [],
            'metadata_fields': [field, second_field]
        })

        assert len(res) == 2
        assert res[0]['key'] == field['key']
        assert res[1]['key'] == second_field['key']

    def test_get_metadata_fieldsets_info_empty_fieldsets(self, field,
                                                         second_field):
        res = AngularApiAdapter()._get_metadata_fieldsets_info(
            fieldsets=[], result=[], fields=[field, second_field]
        )

        assert len(res) == 0

    @mock.patch.object(AngularApiAdapter, '_get_field_info')
    def test_get_metadata_fieldsets_info_flat_fields(self, mock_get_field_info,
                                                     field, second_field):
        mock_get_field_info.side_effect = self.get_res_list()

        res = AngularApiAdapter()._get_metadata_fieldsets_info(
            ('field', 'field2', 'not_existing'), [], [field, second_field]
        )

        assert len(res) == 2
        assert res[0]['key'] == field['key']
        assert res[1]['key'] == second_field['key']

    @mock.patch.object(AngularApiAdapter, '_get_field_info')
    def test_get_metadata_fieldsets_info_list_fields(self, mock_get_field_info,
                                                     field, second_field):
        mock_get_field_info.side_effect = self.get_res_list()

        res = AngularApiAdapter()._get_metadata_fieldsets_info(
            [('field', 'field2', 'not_existing')], [], [field, second_field]
        )

        assert len(res) == 2
        assert res[0]['key'] == field['key']
        assert res[1]['key'] == second_field['key']

    @mock.patch.object(AngularApiAdapter, '_get_field_info')
    def test_get_metadata_fieldsets_info_row_fields(self, mock_get_field_info,
                                                    field, second_field):
        mock_get_field_info.side_effect = self.get_res_list()

        res = AngularApiAdapter()._get_metadata_fieldsets_info(
            [{
                'type': CONTAINER_ROW,
                'fields': ('field', 'field2', 'not_existing')
            }], [], [field, second_field]
        )

        assert len(res) == 1
        assert res[0]['type'] == CONTAINER_ROW
        assert len(res[0]['children']) == 2

    @mock.patch.object(AngularApiAdapter, '_get_field_info')
    def test_get_metadata_fieldsets_info_collapse_fields(
                self, mock_get_field_info, field, second_field
            ):
        mock_get_field_info.side_effect = self.get_res_list()

        res = AngularApiAdapter()._get_metadata_fieldsets_info(
            [{
                'type': CONTAINER_COLLAPSE,
                'name': 'test',
                'collapsed': True,
                'fields': ('field', 'field2', 'not_existing')
            }], [], [field, second_field]
        )

        assert len(res) == 1
        assert res[0]['type'] == CONTAINER_COLLAPSE
        assert len(res[0]['children']) == 2
        assert res[0]['name'] == 'test'
        assert res[0]['collapsed']

    @mock.patch.object(AngularApiAdapter, '_get_field_info')
    def test_get_metadata_fieldsets_info_dict_without_type_fields(
                self, mock_get_field_info, field, second_field
            ):
        mock_get_field_info.side_effect = self.get_res_list()

        res = AngularApiAdapter()._get_metadata_fieldsets_info(
            [{
                'fields': ('field', 'field2', 'not_existing')
            }], [], [field, second_field]
        )

        assert len(res) == 2
        assert res[0]['key'] == field['key']
        assert res[1]['key'] == second_field['key']

    @mock.patch.object(AngularApiAdapter, '_get_field_info')
    def test_get_metadata_fieldsets_info_dict_non_field_type(
                self, mock_get_field_info, field, second_field
            ):
        mock_get_field_info.return_value = self.get_button_field()

        res = AngularApiAdapter()._get_metadata_fieldsets_info(
            [{
                'type': FIELD_BUTTON,
                'action': 'test'
            }], [], [field, second_field]
        )

        assert len(res) == 1
        assert res[0]['type'] == FIELD_BUTTON

    @mock.patch.object(AngularApiAdapter, '_get_field_info')
    def test_get_metadata_fieldsets_info_dict_custom_type_fields(
                self, mock_get_field_info, field, second_field
            ):
        field = self.get_field()
        field.update(type=FIELD_RADIO_GROUP, component_type=FIELD_RADIO_GROUP)
        mock_get_field_info.side_effect = [field, self.get_field()]

        res = AngularApiAdapter()._get_metadata_fieldsets_info(
            [{
                'type': FIELD_RADIO_GROUP,
                'field': field['key']
            }], [], [field, second_field]
        )

        assert len(res) == 1
        assert res[0]['type'] == FIELD_RADIO_GROUP
        assert res[0]['key'] == field['key']

    @mock.patch.object(AngularApiAdapter, '_get_field_info')
    def test_get_metadata_fieldsets_info_dict_custom_type_not_found(
                self, mock_get_field_info, field, second_field
            ):
        mock_get_field_info.return_value = None

        res = AngularApiAdapter()._get_metadata_fieldsets_info(
            [{
                'type': FIELD_BUTTON,
                'action': 'test'
            }], [], [field, second_field]
        )

        assert len(res) == 0


class TestAngularListApiAdapter:

    @pytest.fixture
    def adapter(self):
        return AngularListApiAdapter()

    @pytest.fixture
    def filter_field(self):
        return {
            'key': 'field',
            'type': 'related',
            'label': 'label',
            'endpoint': '/',
            'ui': {
                'label': 'label'
            }
        }

    @pytest.fixture
    def choices_filter_field(self):
        return {
            'key': 'field',
            'type': 'select',
            'label': 'label',
            'choices': [{
                'value': 'val',
                'label': 'label'
            }]
        }

    @pytest.fixture
    def date_filter_field(self):
        return {
            'key': 'field',
            'type': 'date',
            'label': 'label',
        }

    @pytest.fixture
    def display_fields(self):
        return {
            'columns': [{
                'name': 'name',
                'content': [{
                    'type': 'input',
                    'field': 'field'
                }]
            }]
        }

    @pytest.fixture
    def highlight(self):
        return {
            'field': 'field',
            'values': ('val1', ),
        }

    @pytest.fixture
    def adapted_fields(self):
        return [{
            'type': 'input',
            'key': 'field',
        }, {
            'type': 'input',
            'key': 'field1',
        }]

    def test_angular_list_adapter_init(self):
        adapter = AngularListApiAdapter()

        assert adapter.adapted_fields == {}
        assert adapter.fields == []

    def test_get_field_success(self, adapter):
        fields = [{
            'key': 'field',
        }, {
            'key': 'field_1',
        }]

        field = adapter._get_field(fields, 'field')

        assert field['key'] == 'field'

    def test_get_field_none(self, adapter):
        fields = [{
            'key': 'field_2',
        }, {
            'key': 'field_1',
        }]

        field = adapter._get_field(fields, 'field')

        assert field is None

    def test_get_field_empty(self, adapter):
        field = adapter._get_field([], 'field')

        assert field is None

    @mock.patch.object(AngularListApiAdapter, 'adapt_field')
    def test_adapt_field(self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = {
            'type': 'input',
            'key': 'field'
        }

        res = adapter._adapt_field('field', [{'key': 'field'}], ['field'])

        assert res['key'] == 'field'
        assert not res['read_only']

    @mock.patch.object(AngularListApiAdapter, 'adapt_field')
    def test_adapt_field_read_only(self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = {
            'type': 'input',
            'key': 'field'
        }

        res = adapter._adapt_field('field', [{'key': 'field'}])

        assert res['key'] == 'field'
        assert res['read_only']

    @mock.patch.object(AngularListApiAdapter, 'adapt_field')
    def test_adapt_field_in_editables(self, mock_adapt_field, adapter):
        adapter.list_editable = ['field']
        mock_adapt_field.return_value = {
            'type': 'input',
            'key': 'field'
        }

        res = adapter._adapt_field('field', [{'key': 'field'}])

        assert res['key'] == 'field'
        assert not res['read_only']

    @mock.patch.object(AngularListApiAdapter, 'adapt_field')
    def test_adapt_field_without_fields(self, mock_adapt_field, adapter):
        adapter.list_editable = ['field']
        adapter.fields = [{'key': 'field'}]
        mock_adapt_field.return_value = {
            'type': 'input',
            'key': 'field'
        }

        res = adapter._adapt_field('field')

        assert res['key'] == 'field'
        assert not res['read_only']

    @mock.patch.object(AngularListApiAdapter, 'adapt_field')
    def test_adapt_field_not_found(self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = {
            'type': 'input',
            'key': 'field'
        }

        res = adapter._adapt_field('field', [])

        assert res is None

    @mock.patch.object(AngularListApiAdapter, 'adapt_field')
    def test_adapt_field_with_arg(self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = {
            'type': 'input',
            'key': 'field'
        }

        res = adapter._adapt_field('field', [{'key': 'field'}], ['field'],
                                   field_type='input')

        assert res['key'] == 'field'
        assert not res['read_only']

    @mock.patch.object(AngularListApiAdapter, 'adapt_field')
    def test_adapt_field_dict(self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = {
            'type': 'input',
            'key': 'field'
        }

        res = adapter._adapt_field({'field': 'field'}, [{'key': 'field'}],
                                   ['field'], field_type='input')

        assert res['key'] == 'field'
        assert not res['read_only']

    @mock.patch.object(AngularListApiAdapter, 'adapt_field')
    def test_adapt_field_is_formset(self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = {
            'type': 'input',
            'key': 'field'
        }

        adapter.is_formset = True
        res = adapter._adapt_field({'field': 'field'}, [{'key': 'field'}],
                                   ['field'], field_type='input')

        assert res['key'] == 'field'

    @mock.patch.object(AngularListApiAdapter, '_adapt_field')
    def test_get_adapted_field_not_in_list(self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = {
            'type': 'input',
            'key': 'field'
        }

        res = adapter.get_adapted_field('field')

        assert res['key'] == 'field'

    @mock.patch.object(AngularListApiAdapter, '_adapt_field')
    def test_get_adapted_field_dict_not_in_list(self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = {
            'type': 'input',
            'key': 'field'
        }

        res = adapter.get_adapted_field({'field': 'field'})

        assert res['key'] == 'field'

    @mock.patch.object(AngularListApiAdapter, '_adapt_field')
    def test_get_adapted_field_in_list(self, mock_adapt_field, adapter):

        with mock.patch.object(
                AngularListApiAdapter, 'adapted_fields',
                new_callable=mock.PropertyMock) as mock_adapted_fields:

            mock_adapted_fields.return_value = {
                'field': {
                    'type': 'input',
                    'key': 'field',
                    'templateOptions': {
                        'type': 'input',
                    }
                }
            }
            res = adapter.get_adapted_field('field', 'input')

            assert res['key'] == 'field'

    @mock.patch.object(AngularListApiAdapter, '_adapt_field')
    def test_get_adapted_field_invalid(self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = None

        res = adapter.get_adapted_field({'test': 'field'})

        assert res is None

    def test_adapt_actions(self, adapter):
        actions = [{
            'text': 'text',
            'url': 'url',
        }]
        res = adapter._adapt_actions(actions)

        assert 'label' in res
        assert len(res['options']) == 1

    def test_adapt_actions_no_actions(self, adapter):
        res = adapter._adapt_actions([])

        assert 'label' in res
        assert len(res['options']) == 0

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_filers_related_simple(self, mock_get_field,
                                         filter_field, adapter):
        mock_get_field.return_value = filter_field

        res = adapter._adapt_filters(['field'])

        assert len(res) == 1
        assert res[0]['data']['endpoint'] == '/'
        assert res[0]['query'] == 'field'

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_filers_related_ui_label(self, mock_get_field,
                                           filter_field, adapter):
        filter_field = copy.copy(filter_field)
        filter_field['label'] = None
        mock_get_field.return_value = filter_field

        res = adapter._adapt_filters(['field'])

        assert len(res) == 1
        assert res[0]['data']['endpoint'] == '/'
        assert res[0]['query'] == 'field'

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_filers_dict_related(self, mock_get_field,
                                       filter_field, adapter):
        mock_get_field.return_value = filter_field

        res = adapter._adapt_filters([{'field': 'field', 'endpoint': '/'}])

        assert len(res) == 1
        assert res[0]['data']['endpoint'] == '/'
        assert res[0]['query'] == 'field'
        assert res[0]['query'] == 'field'

    @mock.patch('r3sourcer.apps.core_adapter.adapters.api_reverse', return_value='/')
    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_filers_related_endpoint(self, mock_get_field, mock_reverse,
                                           filter_field, adapter):
        filter_field = copy.copy(filter_field)
        filter_field['related_endpoint'] = '/'
        mock_get_field.return_value = filter_field
        mock_reverse.return_value = '/'

        res = adapter._adapt_filters([{'field': 'field'}])

        assert len(res) == 1
        assert res[0]['data']['endpoint'] == '/'
        assert res[0]['query'] == 'field'

    @mock.patch('r3sourcer.apps.core_adapter.utils.api_reverse', return_value='/')
    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_filers_no_related_endpoint(self, mock_get_field, mock_reverse,
                                              filter_field, adapter):
        filter_field = copy.copy(filter_field)
        filter_field['related_endpoint'] = '/'
        mock_get_field.return_value = filter_field
        mock_reverse.side_effect = NoReverseMatch

        res = adapter._adapt_filters([{'field': 'field'}])

        assert len(res) == 0

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_filers_select_simple(self, mock_get_field,
                                        choices_filter_field, adapter):
        mock_get_field.return_value = choices_filter_field

        res = adapter._adapt_filters(['field'])

        assert len(res) == 1
        assert len(res[0]['options']) == 2
        assert res[0]['options'][0]['value'] == ''
        assert res[0]['options'][1]['value'] == 'val'

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_filers_select_callable(self, mock_get_field,
                                          choices_filter_field, adapter):
        mock_get_field.return_value = choices_filter_field

        res = adapter._adapt_filters([{
            'type': FIELD_SELECT,
            'field': 'field',
            'choices': lambda: [{
                'value': 'val',
                'label': 'label'
            }],
        }])

        assert len(res) == 1
        assert len(res[0]['options']) == 2
        assert res[0]['options'][0]['value'] == ''
        assert res[0]['options'][1]['value'] == 'val'

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_filers_select_dict(self, mock_get_field,
                                      choices_filter_field, adapter):
        mock_get_field.return_value = choices_filter_field

        res = adapter._adapt_filters([{
            'field': 'field',
            'choices': [{
                'value': 'val1',
                'label': 'label1'
            }]
        }])

        assert len(res) == 1
        assert len(res[0]['options']) == 2
        assert res[0]['options'][0]['value'] == ''
        assert res[0]['options'][1]['value'] == 'val1'

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_filers_select_no_choices(self, mock_get_field,
                                            choices_filter_field, adapter):
        choices_filter_field = copy.copy(choices_filter_field)
        del choices_filter_field['choices']
        mock_get_field.return_value = choices_filter_field

        res = adapter._adapt_filters([{
            'field': 'field',
        }])

        assert len(res) == 0

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_filers_select_choices_empty(self, mock_get_field,
                                               choices_filter_field, adapter):
        choices_filter_field = copy.copy(choices_filter_field)
        choices_filter_field['choices'] = []
        mock_get_field.return_value = choices_filter_field

        res = adapter._adapt_filters([{
            'field': 'field',
        }])

        assert len(res) == 0

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_filers_date_simple_default_actions(
                self, mock_get_field, date_filter_field, adapter
            ):
        mock_get_field.return_value = date_filter_field

        res = adapter._adapt_filters(['field'])

        assert len(res) == 1
        assert len(res[0]['input']) == 2
        assert len(res[0]['list']) == 3

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_filers_date_simple_actions(
                self, mock_get_field, date_filter_field, adapter
            ):
        date_filter_field = copy.copy(date_filter_field)
        date_filter_field['choices'] = []
        mock_get_field.return_value = date_filter_field

        res = adapter._adapt_filters([{'field': 'field', 'actions': []}])

        assert len(res) == 1
        assert len(res[0]['input']) == 2
        assert len(res[0]['list']) == 0

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_filers_no_type(self, mock_get_field, adapter):
        mock_get_field.return_value = {
            'key': 'field',
            'type': 'test',
            'label': 'label',
        }

        res = adapter._adapt_filters([{'field': 'field', 'actions': []}])

        assert len(res) == 0

    @mock.patch.object(AngularListApiAdapter, '_adapt_actions')
    @mock.patch.object(AngularListApiAdapter, '_adapt_filters')
    @mock.patch.object(AngularListApiAdapter, '_adapt_columns')
    def test_adapt_list_display(self, mock_cols, mock_filters, mock_actions,
                                adapter):
        mock_cols.return_value = []
        mock_filters.return_value = []
        mock_actions.return_value = []

        res = adapter.adapt_list_display([], [], [])

        assert 'columns' in res
        assert 'filters' not in res
        assert 'actions' not in res

    @mock.patch.object(AngularListApiAdapter, '_adapt_actions')
    @mock.patch.object(AngularListApiAdapter, '_adapt_filters')
    @mock.patch.object(AngularListApiAdapter, '_adapt_columns')
    def test_adapt_list_display_with_filters(self, mock_cols, mock_filters,
                                             mock_actions, adapter):
        mock_cols.return_value = []
        mock_filters.return_value = ['field']
        mock_actions.return_value = []

        res = adapter.adapt_list_display([], ['field'], [])

        assert 'columns' in res
        assert 'filters' in res
        assert 'actions' not in res

    @mock.patch.object(AngularListApiAdapter, '_adapt_actions')
    @mock.patch.object(AngularListApiAdapter, '_adapt_filters')
    @mock.patch.object(AngularListApiAdapter, '_adapt_columns')
    def test_adapt_list_display_with_actions(self, mock_cols, mock_filters,
                                             mock_actions, adapter):
        mock_cols.return_value = []
        mock_filters.return_value = []
        mock_actions.return_value = ['field']

        res = adapter.adapt_list_display([], [], ['field'])

        assert 'columns' in res
        assert 'filters' not in res
        assert 'actions' in res

    def test_process_dict_field(self, adapter):
        display_field = {
            'field': 'field',
            'label': 'label',
            'name': 'name',
        }

        res = adapter._process_dict_field(display_field)

        assert res == ('label', 'name', [display_field])

    def test_process_dict_field_without_name(self, adapter):
        display_field = {
            'field': 'field',
            'label': 'label test',
        }

        res = adapter._process_dict_field(display_field)

        assert res == ('label test', 'label_test', [display_field])

    def test_process_dict_field_without_label(self, adapter):
        display_field = {
            'field': 'field',
        }

        res = adapter._process_dict_field(display_field)

        assert res == ('', '', [display_field])

    def test_process_dict_field_fields_without_label(self, adapter):
        display_field = {
            'fields': ['field', 'field1'],
        }

        with pytest.raises(ValueError):
            adapter._process_dict_field(display_field)

    def test_process_dict_field_fields(self, adapter):
        display_field = {
            'fields': ['field', 'field1'],
            'label': 'label',
        }

        res = adapter._process_dict_field(display_field)

        assert res == ('label', 'label', ['field', 'field1'])

    @mock.patch.object(AngularListApiAdapter, 'adapted_fields',
                       new_callable=mock.PropertyMock)
    def test_adapt_ordering(self, mock_adapted_fields, display_fields, adapter):
        mock_adapted_fields.return_value = {
            'field': {
                'type': 'text',
                'key': 'field'
            }
        }

        res = adapter.adapt_ordering(display_fields, ['name'], {}, [])

        assert res[0]['sort']

    @mock.patch.object(AngularListApiAdapter, 'adapted_fields',
                       new_callable=mock.PropertyMock)
    def test_adapt_ordering_asc_order(self, mock_adapted_fields, adapter,
                                      display_fields):
        mock_adapted_fields.return_value = {
            'field': {
                'type': 'text',
                'key': 'field',
            }
        }

        res = adapter.adapt_ordering(display_fields, ['name'], {},
                                     ['another', 'name'])

        assert res[0]['sort']
        assert res[0]['sorted'] == 'asc'

    @mock.patch.object(AngularListApiAdapter, 'adapted_fields',
                       new_callable=mock.PropertyMock)
    def test_adapt_ordering_desc_order(self, mock_adapted_fields, adapter,
                                       display_fields):
        mock_adapted_fields.return_value = {
            'field': {
                'type': 'text',
                'key': 'field',
            }
        }

        res = adapter.adapt_ordering(display_fields, ['name'], {}, ['-name'])

        assert res[0]['sort']
        assert res[0]['sorted'] == 'desc'

    @mock.patch.object(AngularListApiAdapter, 'adapted_fields',
                       new_callable=mock.PropertyMock)
    def test_adapt_ordering_multiple_fields(self, mock_adapted_fields, adapter):
        mock_adapted_fields.return_value = {
            'field': {
                'type': 'text',
                'key': 'field',
            }
        }
        display_fields = {
            'columns': [{
                'name': 'name',
                'content': [{
                    'type': 'input',
                    'field': 'field'
                }, {
                    'type': 'input',
                    'field': 'field2'
                }]
            }]
        }

        res = adapter.adapt_ordering(display_fields, ['name'], {}, ['-name'])

        assert 'sort' not in res[0]

    @mock.patch.object(AngularListApiAdapter, 'adapted_fields',
                       new_callable=mock.PropertyMock)
    def test_adapt_ordering_not_in_adapted(self, mock_adapted_fields, adapter,
                                           display_fields):
        mock_adapted_fields.return_value = {}

        res = adapter.adapt_ordering(display_fields, ['name'], {}, ['-name'])

        assert 'sort' not in res[0]

    @mock.patch.object(AngularListApiAdapter, 'adapted_fields',
                       new_callable=mock.PropertyMock)
    def test_adapt_ordering_mapping(self, mock_adapted_fields, adapter):
        mock_adapted_fields.return_value = {
            'field': {
                'type': 'text',
                'key': 'field'
            }
        }

        display_fields = {
            'columns': [{
                'name': 'name',
                'content': [{
                    'type': 'input',
                    'field': 'field'
                }, {
                    'type': 'input',
                    'field': 'field2'
                }]
            }]
        }

        res = adapter.adapt_ordering(
            display_fields, ['name'], {'name': 'field'}, []
        )

        assert res[0]['sort']
        assert res[0]['sort_field'] == 'field'

    def test_adapt_context_menu(self, adapter, display_fields):
        context_actions = {
            'name': {}
        }

        res = adapter.adapt_context_menu(display_fields, context_actions)

        assert 'context_menu' in res[0]

    def test_adapt_context_menu_no_actions(self, adapter, display_fields):
        res = adapter.adapt_context_menu(display_fields, {})

        assert 'context_menu' not in res[0]

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_highlight(self, mock_get_field, adapter, highlight):
        mock_get_field.return_value = {
            'key': 'field',
            'type': 'checkbox',
            'label': 'label',
        }

        res = adapter.adapt_highlight(highlight)

        assert res['values'] == {'val1': True}

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_highlight_select(self, mock_get_field, adapter, highlight):
        mock_get_field.return_value = {
            'key': 'field',
            'type': 'select',
            'label': 'label',
            'choices': [],
        }

        res = adapter.adapt_highlight(highlight)

        assert res['values'] == {'val1': True}

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_highlight_no_highlight(self, mock_get_field, adapter):
        mock_get_field.return_value = {}

        highlight = {}

        res = adapter.adapt_highlight(highlight)

        assert res is None

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_highlight_no_checkbox_and_select(self, mock_get_field,
                                                    adapter, highlight):
        mock_get_field.return_value = {
            'key': 'field',
            'type': 'text',
        }

        res = adapter.adapt_highlight(highlight)

        assert res is None

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_highlight_select_no_choices(self, mock_get_field,
                                               adapter, highlight):
        mock_get_field.return_value = {
            'key': 'field',
            'type': 'select',
        }

        res = adapter.adapt_highlight(highlight)

        assert res is None

    @mock.patch.object(AngularListApiAdapter, 'get_adapted_field')
    def test_adapt_column_fields_simple_field(self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = {
            'type': 'input',
        }

        res = adapter._adapt_column_fields(['field'])

        assert len(res) == 1
        assert res[0]['field'] == 'field'

    @mock.patch.object(AngularListApiAdapter, 'get_adapted_field')
    def test_adapt_column_fields_simple_field_no_type(self, mock_adapt_field,
                                                      adapter):
        mock_adapt_field.return_value = {}

        res = adapter._adapt_column_fields(['field'])

        assert len(res) == 1
        assert res[0]['field'] == 'field'
        assert res[0]['type'] == 'static'

    @mock.patch.object(AngularListApiAdapter, 'get_adapted_field')
    def test_adapt_column_fields_simple_field_select(self, mock_adapt_field,
                                                     adapter):
        mock_adapt_field.return_value = {
            'type': 'select',
            'templateOptions': {
                'options': [{'value': 'val', 'label': 'label'}]
            }
        }

        res = adapter._adapt_column_fields(['field'])

        assert len(res) == 1
        assert 'values' in res[0]

    @mock.patch.object(AngularListApiAdapter, 'get_adapted_field')
    def test_adapt_column_fields_simple_field_select_no_options(
            self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = {
            'type': 'select',
            'templateOptions': {}
        }

        res = adapter._adapt_column_fields(['field'])

        assert len(res) == 1
        assert 'values' not in res[0]

    @mock.patch.object(AngularListApiAdapter, 'get_adapted_field')
    def test_adapt_column_fields_simple_field_select_adapted_has_options(
            self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = {
            'type': 'select',
            'values': [{'value': 'val', 'label': 'label'}],
            'templateOptions': {
                'options': [{'value': 'val1', 'label': 'label1'}]
            }
        }

        res = adapter._adapt_column_fields(['field'])

        assert len(res) == 1
        assert res[0]['values'] == [{'value': 'val', 'label': 'label'}]

    def test_adapt_column_fields_dict_field_without_field(self, adapter):
        with pytest.raises(ValueError):
            adapter._adapt_column_fields([{}])

    @mock.patch.object(AngularListApiAdapter, 'get_adapted_field')
    def test_adapt_column_fields_dict_field(
            self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = {
            'type': 'input',
        }

        res = adapter._adapt_column_fields([{
            'field': 'field'
        }])

        assert len(res) == 1
        assert res[0]['field'] == 'field'

    @mock.patch.object(AngularListApiAdapter, 'get_adapted_field')
    def test_adapt_column_fields_dict_field_type(
            self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = {
            'type': 'input',
        }

        res = adapter._adapt_column_fields([{
            'field': 'field',
            'type': 'checkbox',
        }])

        assert len(res) == 1
        assert res[0]['type'] == 'checkbox'

    @mock.patch.object(AngularListApiAdapter, 'get_adapted_field')
    def test_adapt_column_fields_dict_fields(
            self, mock_adapt_field, adapter, adapted_fields):
        mock_adapt_field.side_effect = adapted_fields

        res = adapter._adapt_column_fields([{
            'fields': ('field', 'field1'),
            'type': 'link',
        }])

        assert len(res) == 1
        assert len(res[0]['fields']) == 2

    @mock.patch.object(AngularListApiAdapter, 'get_adapted_field')
    def test_adapt_column_fields_dict_fields_without_type(
            self, mock_adapt_field, adapter):
        mock_adapt_field.return_value = None

        with pytest.raises(ValueError):
            adapter._adapt_column_fields([{
                'fields': ('field', 'field1'),
            }])

    @mock.patch.object(AngularListApiAdapter, 'get_adapted_field')
    @mock.patch.object(AngularListApiAdapter, '_adapt_column_fields')
    def test_adapt_columns_simple_field(self, mock_adapt_column,
                                        mock_adapt_field, adapted_fields,
                                        adapter):
        mock_adapt_column.return_value = [adapted_fields[0]]
        mock_adapt_field.return_value = {
            'key': 'field',
            'templateOptions': {
                'label': 'label',
            },
        }

        res = adapter._adapt_columns(['field'])

        assert len(res) == 1
        assert res[0]['name'] == 'field'

    @mock.patch.object(AngularListApiAdapter, 'get_adapted_field')
    @mock.patch.object(AngularListApiAdapter, '_adapt_column_fields')
    def test_adapt_columns_simple_field_without_name(
            self, mock_adapt_column, mock_adapt_field, adapted_fields,
            adapter):
        mock_adapt_column.return_value = [adapted_fields[0]]
        mock_adapt_field.return_value = {
            'templateOptions': {
                'label': 'label',
            },
        }

        with pytest.raises(KeyError):
            adapter._adapt_columns(['field'])

    @mock.patch.object(AngularListApiAdapter, 'get_adapted_field')
    @mock.patch.object(AngularListApiAdapter, '_adapt_column_fields')
    def test_adapt_columns_simple_field_without_label(
            self, mock_adapt_column, mock_adapt_field, adapted_fields,
            adapter):
        mock_adapt_column.return_value = [adapted_fields[0]]
        mock_adapt_field.return_value = {
            'key': 'field',
            'templateOptions': {},
        }

        with pytest.raises(KeyError):
            adapter._adapt_columns(['field'])

    @mock.patch.object(AngularListApiAdapter, '_adapt_column_fields')
    def test_adapt_columns_list_fields(self, mock_adapt_column, adapter,
                                       adapted_fields):
        mock_adapt_column.return_value = adapted_fields

        res = adapter._adapt_columns([('name', ('field', 'field1'))])

        assert len(res) == 1
        assert len(res[0]['content']) == 2
        assert res[0]['name'] == 'name'

    def test_adapt_columns_list_fields_not_two(self, adapter):

        with pytest.raises(ValueError):
            adapter._adapt_columns([('name', )])

    def test_adapt_columns_list_fields_not_list(self, adapter):
        with pytest.raises(ValueError):
            adapter._adapt_columns([('name', 'test')])

    @mock.patch.object(AngularListApiAdapter, '_process_dict_field')
    @mock.patch.object(AngularListApiAdapter, '_adapt_column_fields')
    def test_adapt_columns_dict_field(self, mock_adapt_column,
                                      mock_process_dict, adapted_fields,
                                      adapter):
        mock_adapt_column.return_value = [adapted_fields[0]]
        mock_process_dict.return_value = 'label', 'name', ['field']

        res = adapter._adapt_columns([{'field': 'field'}])

        assert len(res) == 1
        assert res[0]['name'] == 'name'
        assert len(res[0]['content']) == 1

    def test_adapt_buttons(self, adapter):
        buttons = [
            {
                'label': 'label',
                'endpoint': 'endpoint'
            }
        ]

        res = adapter.adapt_buttons(buttons)

        assert len(res) == 1
        assert 'endpoint' in res[0]

    def test_adapt_buttons_action(self, adapter):
        buttons = [
            {
                'label': 'label',
                'action': 'action'
            }
        ]

        res = adapter.adapt_buttons(buttons)

        assert len(res) == 1
        assert 'action' in res[0]

    def test_adapt_buttons_empty(self, adapter):
        buttons = []

        res = adapter.adapt_buttons(buttons)

        assert len(res) == 0

    def test_adapt_buttons_not_dict(self, adapter):
        buttons = ['button']

        res = adapter.adapt_buttons(buttons)

        assert len(res) == 0

    def test_adapt_tabs(self, adapter):
        tab = {
            'label': 'label',
            'fields': ['field'],
            'is_collapsed': False,
        }
        tabs = [tab]

        res = adapter.adapt_tabs(tabs)

        assert len(res) == 1
        assert res[0] == tab

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_tabs_without_label(self, mock_get_field, adapter):
        mock_get_field.return_value = {'ui': {'label': 'field'}}

        tab = {
            'fields': ['field'],
            'is_collapsed': False,
        }
        tabs = [tab]

        res = adapter.adapt_tabs(tabs)

        assert len(res) == 1
        assert 'label' in res[0]
        assert res[0]['label'] == 'field'

    @mock.patch.object(AngularListApiAdapter, '_get_field')
    def test_adapt_tabs_list(self, mock_get_field, adapter):
        mock_get_field.return_value = {'ui': {'label': 'field'}}
        tabs = [['field']]

        res = adapter.adapt_tabs(tabs)

        assert len(res) == 1
        assert 'label' in res[0]
        assert res[0]['label'] == 'field'

    def test_adapt_tabs_string(self, adapter):
        tabs = ['field']

        res = adapter.adapt_tabs(tabs)

        assert len(res) == 0

    def test_adapt_tabs_empty(self, adapter):
        tabs = []

        res = adapter.adapt_tabs(tabs)

        assert len(res) == 0
