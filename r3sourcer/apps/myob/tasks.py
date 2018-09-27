import datetime

from celery import shared_task
from celery.utils.log import get_task_logger

from django.db.models import Q

from r3sourcer.apps.candidate.models import CandidateContact
from r3sourcer.apps.core.models import Company, Invoice
from r3sourcer.apps.core.tasks import one_task_at_the_same_time
from r3sourcer.apps.core.utils.user import get_default_company
from r3sourcer.apps.hr.models import TimeSheet
from r3sourcer.apps.myob.api.wrapper import MYOBServerException, MYOBClient
from r3sourcer.apps.myob.helpers import get_myob_client
from r3sourcer.apps.myob.models import MYOBSyncObject, MYOBRequestLog, MYOBCompanyFileToken
from r3sourcer.apps.myob.services.candidate import CandidateSync
from r3sourcer.apps.myob.services.invoice import InvoiceSync
from r3sourcer.apps.myob.services.timesheet import TimeSheetSync
from r3sourcer.apps.myob.services.utils import sync_candidate_contacts_to_myob, sync_companies_to_myob
from r3sourcer.celeryapp import app


logger = get_task_logger(__name__)


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


@app.task(bind=True)
@one_task_at_the_same_time()
@retry_on_myob_error
def sync_to_myob(self):
    """
    Sync candidate contacts, clients, jobsites to myob.
    """

    companies = Company.objects.filter(
        Q(myob_settings__invoice_company_file__isnull=False) |
        Q(myob_settings__timesheet_company_file__isnull=False)
    )
    for company in companies:
        company_settings = getattr(company, 'myob_settings', None)

        if company_settings and company_settings.timesheet_company_file:
            myob_client = get_myob_client(cf_id=company_settings.timesheet_company_file.cf_id)
            sync_candidate_contacts_to_myob(myob_client, company)

        if company_settings and company_settings.invoice_company_file:
            myob_client = get_myob_client(cf_id=company_settings.invoice_company_file.cf_id)
            sync_companies_to_myob(myob_client, company)


@app.task(bind=True)
@one_task_at_the_same_time()
@retry_on_myob_error
def sync_timesheets(self):
    companies = Company.objects.filter(type=Company.COMPANY_TYPES.master)

    for company in companies:
        candidates = CandidateContact.objects.owned_by(company)

        company_settings = getattr(company, 'myob_settings', None)
        if not company_settings or not company_settings.timesheet_company_file:
            logger.warn('Company %s has no TimeSheet Company Files configured', str(company))
            continue

        sync_service = TimeSheetSync(cf_id=company_settings.timesheet_company_file.cf_id, company=company)

        for candidate in candidates:
            sync_service.sync_to_myob(candidate)

        logger.warn('Sync Timesheets for company %s finished', str(company))


@app.task(bind=True)
@one_task_at_the_same_time
def clean_myob_request_log(self):
    """
    Clean myob request logs from db.
    """

    today = datetime.date.today()
    MYOBRequestLog.objects.filter(created__date__lt=today).delete()


@shared_task
def sync_invoice(invoice_id):
    invoice = Invoice.objects.get(id=invoice_id)
    company = invoice.provider_company

    if company.myob_settings.invoice_company_file:
        company_file = company.myob_settings.invoice_company_file
        cf_token = company_file.tokens.first()
    else:
        cf_token = MYOBCompanyFileToken.objects.filter(company=company).first()

    client = MYOBClient(cf_data=cf_token)
    service = InvoiceSync(myob_client=client, company=company)

    params = {"$filter": "Number eq '%s'" % invoice.number}
    synced_invoice = client.api.Sale.Invoice.TimeBilling.get(params=params)

    if synced_invoice['Count']:
        if synced_invoice['Count'] > 1:
            raise Exception("Got 2 or more invoices with id %s from MYOB." % invoice.id)

        synced_invoice_lines = synced_invoice['Items'][0]['Lines']

        if len(synced_invoice_lines) < invoice.invoice_lines.count():
            service.sync_to_myob(invoice, partial=True)
    else:
        service.sync_to_myob(invoice)


@app.task(bind=True)
@one_task_at_the_same_time()
@retry_on_myob_error
def sync_timesheet(self, timesheet_id):
    try:
        timesheet = TimeSheet.objects.get(id=timesheet_id)
    except TimeSheet.DoesNotExist:
        logger.warn('TimeSheet with id=%s does not exist')
        return

    service = TimeSheetSync.from_candidate(timesheet.job_offer.candidate_contact)
    service.sync_single_to_myob(timesheet)
