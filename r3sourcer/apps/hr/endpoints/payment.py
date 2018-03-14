from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.core import models
from r3sourcer.apps.core.api import endpoints
from r3sourcer.apps.core.utils.text import format_lazy
from r3sourcer.apps.core_adapter import constants
from r3sourcer.apps.core_adapter.utils import api_reverse_lazy

from ..api.viewsets import InvoiceViewset


__all__ = [
    'InvoiceEndpoint'
]


class InvoiceEndpoint(endpoints.ApiEndpoint):

    model = models.Invoice
    base_viewset = InvoiceViewset
    list_display = (
        'customer_company', 'date', 'total', 'tax', 'total_with_tax', 'period', 'separation_rule', {
            'type': constants.FIELD_TEXT,
            'field': 'number',
            'read_only': False,
        }, {
            'type': constants.FIELD_BUTTON,
            'action': 'previewInvoice',
            'endpoint': format_lazy(
                '{}{{id}}/pdf/',
                api_reverse_lazy('core/invoices')
            ),
            'text': _('Preview'),
            'icon': 'fa-eye',
            'field': 'id',
        }, {
            'type': constants.FIELD_BUTTON,
            'action': 'printInvoice',
            'endpoint': format_lazy(
                '{}{{id}}/pdf/',
                api_reverse_lazy('core/invoices')
            ),
            'text': _('Print'),
            'icon': 'fa-print',
            'field': 'id',
        },
        {
            'type': constants.FIELD_BUTTON,
            'icon': 'fa-external-link',
            'text': _('Approve'),
            'endpoint': format_lazy(
                '{}{{id}}/approve/',
                api_reverse_lazy('core/invoices')
            ),
            'field': 'id',
            'action': constants.DEFAULT_ACTION_POST,
    })

    fieldsets = ({
        'type': constants.CONTAINER_ROW,
        'label': '{customer_company.__str__} - {date}',
        'fields': (
            {
                'type': constants.CONTAINER_COLUMN,
                'fields': (
                    {
                        'label': _('Provider Company'),
                        'field': 'provider_company',
                        'type': constants.FIELD_RELATED,
                    }, {
                        'label': _('Provider Representative'),
                        'field': 'provider_representative',
                        'type': constants.FIELD_RELATED,
                    }, {
                        'label': _('Customer Company'),
                        'field': 'customer_company',
                        'type': constants.FIELD_RELATED,
                    },
                ),
            }, {
                'type': constants.CONTAINER_COLUMN,
                'fields': (
                    {
                        'type': constants.FIELD_TEXT,
                        'field': 'total_with_tax',
                        'label': _('Total wit GST'),
                    }, {
                        'type': constants.FIELD_TEXT,
                        'field': 'total',
                        'label': _('Total'),
                    }, {
                        'type': constants.FIELD_TEXT,
                        'field': 'tax',
                        'label': _('GST'),
                    }, 'is_paid', {
                        'type': constants.FIELD_DATE,
                        'field': 'paid_at',
                        'label': _('Paid at',)
                    }, 'currency', {
                        'type': constants.FIELD_TEXT,
                        'field': 'number',
                        'label': _('Invoice No'),
                    }, {
                        'type': constants.FIELD_TEXT,
                        'field': 'order_number',
                        'label': _('Your Order No'),
                    }, 'period', 'separation_rule', 'date'
                ),
            },
        ),
    }, {
        'type': constants.FIELD_LIST,
        'field': 'id_',
        'query': {
            'invoice': '{id}',
        },
        'label': _('Invoice Lines'),
        'add_label': _('Add'),
        'endpoint': api_reverse_lazy('core/invoicelines'),
        'prefilled': {
            'invoice': '{id}',
        }
    }, )

    filter_fields = ['customer_company']
