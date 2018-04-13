import datetime

from celery import shared_task
from celery.utils.log import get_task_logger

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

    companies = Company.objects.filter(company_file_tokens__isnull=False)
    for company in companies:
        myob_client = get_myob_client_for_account(company)

        # do:
        # sync each class
        sync_candidate_contacts_to_myob(myob_client, company)
        sync_companies_to_myob(myob_client, company)
        # done;


@app.task(bind=True)
@one_task_at_the_same_time()
@retry_on_myob_error
def sync_timesheets(self):
    timesheets = TimeSheet.objects.filter(
        candidate_submitted_at__isnull=False,
        supervisor_approved_at__isnull=False
    ).select_related('job_offer__shift__date__job__jobsite', 'job_offer__candidate_contact')

    company = get_default_company()
    myob_client = get_myob_client(company=company)
    sync_service = TimeSheetSync(myob_client, company=company)
    candidate_service = CandidateSync(myob_client, company=company)

    _service_cache = {
        None: (sync_service, candidate_service),
    }

    for timesheet in timesheets:
        company = timesheet.regular_company or timesheet.master_company
        cft = company and company.myob_settings.get_client_myob_company_file()

        if cft is not None and cft not in _service_cache:
            myob_client = get_myob_client(cf_id=cft.company_file.id)
            sync_service = TimeSheetSync(myob_client, company=company)
            candidate_service = CandidateSync(myob_client, company=company)
            _service_cache[cft.id] = (sync_service, candidate_service)
        else:
            sync_service, candidate_service = _service_cache.get(cft and cft.id)

        candidate = timesheet.job_offer.candidate_contact
        updated_at = candidate.updated_at

        sync_obj = MYOBSyncObject.objects.filter(
            model='CandidateContact', company=company, record=candidate.id
        ).first()
        if not sync_obj or sync_obj.synced_at <= updated_at:
            candidate_service.sync_to_myob(candidate)

        sync_service.sync_to_myob(timesheet)

    print("sync Timesheets {} finished".format(TimeSheetSync))


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

    if company.company_settings.invoice_company_file:
        company_file = company.company_settings.invoice_company_file
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
