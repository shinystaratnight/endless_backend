from r3sourcer.apps.core.models.core import Invoice
from r3sourcer.apps.myob.api.wrapper import MYOBServerException, MYOBClient
from r3sourcer.apps.myob.helpers import get_myob_client
from r3sourcer.apps.myob.models import MYOBCompanyFileToken
from r3sourcer.apps.myob.services.invoice import InvoiceSync


def retry_on_myob_error(origin_task):
    def wrap(self, *args, **kwargs):
        try:
            origin_task(self, *args, **kwargs)
        except MYOBServerException:
            self.retry(args=args, kwargs=kwargs, countdown=60)
    wrap.__name__ = origin_task.__name__
    wrap.__module__ = origin_task.__module__
    return wrap


def get_myob_client_for_account(company):
    myob_client = get_myob_client(company=company)
    if myob_client:
        myob_client.init_api()
    return myob_client


def sync_invoice(invoice_id):
    invoice = Invoice.objects.get(id=invoice_id)
    company = invoice.provider_company
    cf_token = MYOBCompanyFileToken.objects.filter(company=company).first()
    client = MYOBClient(cf_data=cf_token)
    service = InvoiceSync(myob_client=client, company=company)

    params = {"$filter": "Number eq '%s'" % invoice.number}
    synced_invoice = client.api.Sale.Invoice.TimeBilling.get(params=params)

    if synced_invoice['Count']:
        if synced_invoice['Count'] > 1:
            raise Exception("Invoice with id %s is already synced" % invoice.id)

        synced_invoice_lines = synced_invoice['Items'][0]['Lines']

        if len(synced_invoice_lines) < invoice.invoice_lines.count():
            service.sync_to_myob(invoice, partial=True)

        raise Exception("Invoice with id %s is already synced" % invoice.id)
    else:
        service.sync_to_myob(invoice)
