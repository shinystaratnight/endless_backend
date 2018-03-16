import datetime

from r3sourcer.apps.core.models import Company
from r3sourcer.apps.core.tasks import one_task_at_the_same_time
from r3sourcer.apps.hr.models import TimeSheet
from r3sourcer.apps.myob.api.wrapper import MYOBServerException
from r3sourcer.apps.myob.helpers import get_myob_client
from r3sourcer.apps.myob.models import MYOBSyncObject, MYOBRequestLog
from r3sourcer.apps.myob.services.candidate import CandidateSync
from r3sourcer.apps.myob.services.timesheet import TimeSheetSync
from r3sourcer.apps.myob.services.utils import sync_candidate_contacts_to_myob, sync_companies_to_myob
from r3sourcer.celeryapp import app


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
def sync_timesheets(model, sync_service_cls):
    timesheets = TimeSheet.objects.filter(
        candidate_submitted_at__isnull=False,
        supervisor_approved_at__isnull=False
    ).distinct()

    # TODO: get right company
    company = Company.objects.filter(company_file_tokens__isnull=False).first()
    if not company:
        return

    myob_client = get_myob_client(company=company)
    sync_service = TimeSheetSync(myob_client, company=company)
    candidate_service = CandidateSync(myob_client, company=company)

    for timesheet in timesheets:
        candidate = timesheet.vacancy_offer.candidate_contact
        sync_obj = MYOBSyncObject.objects.filter(
            model='CandidateContact', company=company, record=candidate.id
        ).first()
        updated_at = candidate.updated_at
        if not sync_obj or sync_obj.synced_at <= updated_at:
            candidate_service.sync_to_myob(candidate)
        sync_service.sync_to_myob(timesheet)

    print("sync {} {} finalized".format(model, TimeSheetSync))


@app.task(bind=True)
@one_task_at_the_same_time
def clean_myob_request_log(self):
    """
    Clean myob request logs from db.
    """

    today = datetime.date.today()
    MYOBRequestLog.objects.filter(created__date__lt=today).delete()
