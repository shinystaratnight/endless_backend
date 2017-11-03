from .helpers import get_myob_client
from .services import (
    sync_recruitee_contacts_to_myob, sync_jobsites_to_myob,
    sync_clients_to_myob, sync_employment_classification_from_myob,
    sync_bookings_to_myob, sync_invoices_from_myob,
    sync_superannuation_fund_from_myob, TimeSheetSync, BookingSync,
    RecruiteeSync, JobsiteSync, APP_MODEL_MAPPINGS, RECRUITEE_CONTACT, CLIENT
)
from .api.wrapper import MYOBServerException


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
