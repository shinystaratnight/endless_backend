import logging
import pytz
from pytz.exceptions import UnknownTimeZoneError
from calendar import monthrange
from itertools import chain
from uuid import UUID # not remove
from timezonefinder import TimezoneFinder

from datetime import datetime, date, time, timedelta
from collections import defaultdict
from functools import reduce
from urllib.parse import urlparse

from django.db.models import Q
from django.utils import timezone, formats
from django.template.defaulttags import register
from django.templatetags.static import static

from r3sourcer.apps.candidate.models import CandidateContact
from r3sourcer.apps.core.models import InvoiceRule, Invoice
from r3sourcer.apps.core.utils.geo import calc_distance, MODE_TRANSIT
from r3sourcer.celeryapp import app


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
    if distance != -1 and distance["distance"]:
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
        is_public = contact.candidate_contacts.transportation_to_work == CandidateContact.TRANSPORTATION_CHOICES.public
        if hasattr(contact, 'candidate_contacts') and is_public:
            contacts_dict[MODE_TRANSIT].append(contact)
        else:
            contacts_dict[None].append(contact)

    for mode, contact_list in contacts_dict.items():
        addresses = [c.address.get_full_address() for c in contact_list]
        jobsite_address = jobsite.get_address()
        if jobsite_address is None:
            continue

        result = calc_distance(jobsite_address.get_full_address(), addresses, mode=mode)
        if not result:
            return bool(result)

        if len(contact_list) == 1:
            result = [result]

        for distance, contact in zip(result[0], contact_list):
            create_or_update_distance_cache(contact, jobsite, distance)

    return True


def get_jo_sms_sending_task(job_offer):  # pragma: no cover
    if job_offer.is_first() and not job_offer.is_accepted():
        from r3sourcer.apps.hr.tasks import send_jo_confirmation_sms as task
    elif job_offer.is_recurring():
        from r3sourcer.apps.hr.tasks import send_recurring_jo_confirmation_sms as task
    else:
        # FIXME: send job confirmation SMS because there is pending job's JOs for candidate
        from r3sourcer.apps.hr.tasks import send_jo_confirmation_sms as task

    return task


def send_jo_rejection(job_offer):  # pragme: no cover
    from r3sourcer.apps.hr.tasks import send_placement_rejection_sms
    send_placement_rejection_sms.delay(job_offer.pk)


def meters_to_km(meters):
    """
    Converts meters to kilometers
    """
    if meters:
        return round(int(meters) / 1000, 1)
    else:
        return 0


def seconds_to_hrs(seconds):
    """
    Converts seconds to hours
    """
    minutes = int(seconds) // 60
    hours = minutes // 60
    return "%02d:%02d" % (hours, minutes % 60)


def get_invoice_dates(invoice_rule, timesheet=None):
    """
    Accepts invoice rule and returns date_from and date_to needed for invoice generation based on period setting.
    """

    date_from = None
    date_to = None
    today = date.today()

    if timesheet:
        today = timezone.localtime(timesheet.shift_started_at).date()

    if invoice_rule.period == InvoiceRule.PERIOD_CHOICES.daily:
        date_from = today
        date_to = date_from + timedelta(days=1)
    elif invoice_rule.period == InvoiceRule.PERIOD_CHOICES.weekly:
        date_from = today - timedelta(today.weekday())
        date_to = date_from + timedelta(days=7)
    elif invoice_rule.period == InvoiceRule.PERIOD_CHOICES.fortnightly:
        if invoice_rule.last_invoice_created:
            last_invoice_date = invoice_rule.last_invoice_created
            first_invoice_day = last_invoice_date - timedelta(days=last_invoice_date.weekday())

            date_from = first_invoice_day
            while True:
                days_spent = (today - date_from).days

                if days_spent > 14:
                    date_from += timedelta(days=14)
                else:
                    break

            date_to = date_from + timedelta(days=14)
        else:
            date_from = today - timedelta(today.weekday())
            date_to = date_from + timedelta(days=14)

    elif invoice_rule.period == InvoiceRule.PERIOD_CHOICES.monthly:
        date_to = today.replace(day=1) - timedelta(1)
        date_from = date_to.replace(day=1)

    if not date_from:
        raise Exception("Wrong invoice rule period.")

    return date_from, date_to


def get_invoice(company, date_from, date_to, timesheet, recreate=False):
    """
    Checks if needed invoice already exists and returns it to update with new timesheets.
    """
    invoice = None
    invoice_rule = company.invoice_rules.first()

    try:
        qry = Q(
            invoice_lines__date__gte=date_from, invoice_lines__date__lt=date_to,
        )

        if recreate:
            qry = Q()

        if invoice_rule.separation_rule == InvoiceRule.SEPARATION_CHOICES.one_invoce:
            invoice = Invoice.objects.filter(
                qry,
                customer_company=company, approved=False
            ).latest('date')
        elif invoice_rule.separation_rule == InvoiceRule.SEPARATION_CHOICES.per_jobsite:
            jobsite = timesheet.job_offer.shift.date.job.jobsite
            invoice = Invoice.objects.filter(
                qry,
                invoice_lines__timesheet__job_offer__shift__date__job__jobsite=jobsite,
                approved=False
            ).latest('date')
        elif invoice_rule.separation_rule == InvoiceRule.SEPARATION_CHOICES.per_candidate:
            candidate = timesheet.job_offer.candidate_contact
            invoice = Invoice.objects.filter(
                qry,
                customer_company=company, invoice_lines__timesheet__job_offer__candidate_contact=candidate,
                approved=False
            ).latest('date')
    except Exception:
        pass

    return invoice


def send_supervisor_timesheet_approve(timesheet, force=False, not_agree=False):
    from r3sourcer.apps.hr.tasks import send_supervisor_timesheet_sign
    if not_agree:
        date_time = get_jobsite_date_time(job=timesheet.job_offer.job, date_time=timezone.localtime()) + timedelta(hours=4)
        send_supervisor_timesheet_sign.apply_async(
            args=[timesheet.supervisor.id, timesheet.id, force], eta=date_time)
    else:
        send_supervisor_timesheet_sign.apply_async(args=[timesheet.supervisor.id, timesheet.id, force], countdown=10)


def send_job_confirmation_sms(job):
    from r3sourcer.apps.hr.tasks import send_job_confirmation_sms
    send_job_confirmation_sms.apply_async(args=[job.id], countdown=10)


def schedule_auto_approve_timesheet(timesheet):
    from r3sourcer.apps.hr.tasks import auto_approve_timesheet
    for task in chain.from_iterable(app.control.inspect().scheduled().values()):
        if str(eval(task['request']['args'])[0]) == str(timesheet.id) and task['request']['name'] == \
                'r3sourcer.apps.hr.tasks.auto_approve_timesheet':
            app.control.revoke(task['request']['id'], terminate=True, signal='SIGKILL')
    date_time = get_jobsite_date_time(job=timesheet.job_offer.job, date_time=timezone.localtime()) + timedelta(hours=4)
    auto_approve_timesheet.apply_async(args=[timesheet.id],
                                       eta=date_time)


def format_dates_range(dates_list):
    def _cmp_dates(value, element):
        if not value:
            return [[element]]
        current_group = value[-1]
        if element - current_group[-1] == timedelta(days=1):
            current_group.append(element)
        else:
            value.append([element])
        return value
    res_dates = reduce(_cmp_dates, dates_list, [])

    results = []
    for dates in res_dates:
        if len(dates) > 2:
            results.append('{}-{}'.format(
                formats.date_format(dates[0], 'd/m'),
                formats.date_format(dates[-1], 'd/m')
            ))
        else:
            results.extend([formats.date_format(fulldate, 'd/m') for fulldate in dates])

    return results


@register.simple_tag(takes_context=True)
def absstatic(context, path):
    static_url = static(path)
    parsed_url = urlparse(static_url)
    if not parsed_url.netloc:
        request = context['request']
        return request.build_absolute_uri(static_url)
    return static_url


@register.filter
def get_hours(time_delta):
    if not time_delta:
        return '0'
    hours = time_delta.total_seconds() / 3600
    return '{0:.2f}'.format(hours)


def get_jobsite_date_time(job, date_time):
    tf = TimezoneFinder(in_memory=True)
    try:
        time_zone = pytz.timezone(tf.timezone_at(lng=job.jobsite.address.longitude, lat=job.jobsite.address.latitude))
    except UnknownTimeZoneError:
        time_zone = 'Australia/Sydney'
    jobsite_time = date_time.replace(tzinfo=time_zone)
    return jobsite_time
