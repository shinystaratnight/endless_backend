from r3sourcer.apps.candidate.models import CandidateContact
from r3sourcer.apps.core.models import Company
from r3sourcer.apps.hr.models import TimeSheet
from r3sourcer.apps.myob.services.candidate import CandidateSync
from r3sourcer.apps.myob.services.company import CompanySync


def sync_candidate_contacts_to_myob(myob_client=None, account=None):
    """
    Sync candidate contacts to myob service.
    Sync would be used for only candidate contacts on active state and with signed time sheets.

    :param myob_client: object api.client
    :param account: object Account
    :return:
    """

    sync = CandidateSync(myob_client, account)

    # get ids only signed time sheets
    candidates_with_signed_timesheets = TimeSheet.objects.filter(
        candidate_submitted_at__isnull=False,
        supervisor_approved_at__isnull=False,
    ).values_list('job_offer__candidate_contact__id', flat=True)

    # get only active candidate contacts
    candidate_contacts = CandidateContact.objects.filter(id__in=candidates_with_signed_timesheets).distinct()

    for candidate_contact in candidate_contacts:
        sync.sync_to_myob(candidate_contact)


def sync_companies_to_myob(myob_client=None, account=None):
    sync = CompanySync(myob_client, account)

    companies = Company.objects.filter()

    for company in companies:
        sync.sync_to_myob(company)
