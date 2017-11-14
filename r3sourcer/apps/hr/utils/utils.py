import logging

from datetime import datetime, date, time, timedelta
from collections import defaultdict

from django.utils import timezone

from r3sourcer.apps.core.utils.geo import calc_distance, GeoException, OVER_QUERY_LIMIT, MODE_TRANSIT, MODE_DRIVING
from r3sourcer.apps.candidate.models import CandidateContact


log = logging.getLogger(__name__)

WEEKDAY_MAP = {
    0: 'monday',
    1: 'tuesday',
    2: 'wednesday',
    3: 'thursday',
    4: 'friday',
    5: 'saturday',
    6: 'sunday',
}


def today_7_am():
    return timezone.make_aware(datetime.combine(date.today(), time(7, 0)))


def today_12_pm():
    return timezone.make_aware(datetime.combine(date.today(), time(12, 0)))


def today_12_30_pm():
    return timezone.make_aware(datetime.combine(date.today(), time(12, 30)))


def today_3_30_pm():
    return timezone.make_aware(datetime.combine(date.today(), time(15, 30)))


def tomorrow_7_am():
    return today_7_am() + timedelta(days=1)


def tomorrow():
    return date.today() + timedelta(days=1)


def today_5_am():
    return timezone.make_aware(datetime.combine(date.today(), time(5, 0)))


def tomorrow_5_am():
    return today_5_am() + timedelta(days=1)


def tomorrow_end_5_am():
    return tomorrow_5_am() + timedelta(days=1)


def _time_diff(start, end):
    return timedelta(
        hours=end.hour - start.hour,
        minutes=end.minute - start.minute,
        seconds=end.second - start.second
    )


def get_invoice_rule(company):
    if company.invoice_rules.exists():
        return company.invoice_rules.first()
    else:
        master_company = company.get_master_company()[0]
        return master_company.invoice_rules.first()


def get_payslip_rule(company):
    if company.payslip_rules.exists():
        return company.payslip_rules.first()
    else:
        master_company = company.get_master_company()[0]
        return master_company.payslip_rules.first()


def create_or_update_distance_cache(contact, jobsite, distance):
    from ..models import ContactJobsiteDistanceCache
    if distance != -1:
        updated_values = {
            "jobsite": jobsite,
            "contact": contact,
            "distance": distance["distance"],
            "time": distance["duration"]
        }

        obj, created = ContactJobsiteDistanceCache.objects.update_or_create(
            jobsite=jobsite, contact=contact, defaults=updated_values
        )


def calculate_distances_for_jobsite(contacts, jobsite):
    """
    Calculates and save distances between jobsite and contacts
    :param contacts: contacts list
    :param jobsite: jobsite object
    :return: limit of queries is not reached
    """
    contacts_dict = defaultdict(list)
    for contact in contacts:
        if hasattr(contact, 'candidate_contacts')\
                and contact.recruitee_contacts.transportation_to_work == CandidateContact.TRANSPORTATION_CHOICES.public:
            contacts_dict[MODE_TRANSIT].append(contact)
        else:
            contacts_dict[None].append(contact)

    for mode, contact_list in contacts_dict.items():
        addresses = [c.get_full_address() for c in contact_list]
        try:
            distancematrix = calc_distance(jobsite.get_full_address(), addresses, mode=mode)[0]
            if distancematrix is not None:
                for distance, contact in zip(distancematrix, contact_list):
                    create_or_update_distance_cache(contact, jobsite, distance)
        except GeoException as e:
            if e.status == OVER_QUERY_LIMIT:
                return False

    return True