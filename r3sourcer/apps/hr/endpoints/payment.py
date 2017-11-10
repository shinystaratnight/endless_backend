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
        'customer_company', 'date', 'total', 'tax', 'total_with_tax', {
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
        }
    )
