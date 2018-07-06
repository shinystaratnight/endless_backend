from r3sourcer.apps.core import models
from r3sourcer.apps.core.api import endpoints
from r3sourcer.apps.hr.api import filters

from ..api.viewsets import InvoiceViewset


__all__ = [
    'InvoiceEndpoint'
]


class InvoiceEndpoint(endpoints.ApiEndpoint):

    model = models.Invoice
    base_viewset = InvoiceViewset
    filter_class = filters.InvoiceFilter
