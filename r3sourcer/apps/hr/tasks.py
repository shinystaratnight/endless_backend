import operator
from datetime import timedelta, date, time, datetime

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db import transaction, models
from django.template.loader import get_template
from django.utils import formats
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _
from filer.models import File, Folder

from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.tasks import one_sms_task_at_the_same_time
from r3sourcer.apps.core.utils import companies as core_companies_utils
from r3sourcer.apps.email_interface.models import EmailMessage
from r3sourcer.apps.email_interface.utils import get_email_service
from r3sourcer.apps.hr import models as hr_models
from r3sourcer.apps.hr.payment.base import calc_worked_delta
from r3sourcer.apps.hr.utils import utils
from r3sourcer.apps.login.models import TokenLogin
from r3sourcer.apps.myob.helpers import get_myob_client
from r3sourcer.apps.pricing.models import RateCoefficientModifier, PriceListRate
from r3sourcer.apps.pricing.services import CoefficientService
from r3sourcer.apps.pricing.utils.utils import format_timedelta
from r3sourcer.apps.sms_interface.helpers import get_sms_template
from r3sourcer.apps.sms_interface.models import SMSMessage
from r3sourcer.apps.sms_interface.utils import get_sms_service
from r3sourcer.celeryapp import app
from r3sourcer.helpers.datetimes import utc_now, tz2utc, date2utc_date

logger = get_task_logger(__name__)

GOING_TO_WORK, SHIFT_ENDING, RECRUITEE_SUBMITTED, SUPERVISOR_DECLINED = range(4)


@shared_task(queue='hr')
def update_all_distances():

    all_calculated_jobsites = hr_models.Jobsite.objects.filter(
        id__in=hr_models.ContactJobsiteDistanceCache.objects.filter(
            updated_at__isnull=True
        ).values('jobsite')
    )

    for jobsite in all_calculated_jobsites:
        if not (jobsite.latitude == 0 and jobsite.longitude == 0):

            contacts = core_models.Contact.objects.filter(distance_caches__jobsite=jobsite)
            if not utils.calculate_distances_for_jobsite(contacts, jobsite):
                break


def send_job_offer_sms(job_offer, tpl_id, action_sent=None):
    """
    Send job offer sms with specific template.

    :param job_offer: JobOffer
    :param tpl_id: SMSTemplate UUID
    :param action_sent: str Model field for waiting sms reply
    :return:
    """
    try:
        sms_interface = get_sms_service()
    except ImportError:
        logger.exception('Cannot load SMS service')
        return

    target_date_and_time = formats.date_format(job_offer.start_time_tz, settings.DATETIME_FORMAT)

    if utc_now() >= job_offer.start_time_utc:
        target_date_and_time = "ASAP"

    master_company = job_offer.candidate_contact.contact.get_closest_company()
    data_dict = {
        'job_offer': job_offer,
        'job': job_offer.job,
        'jobsite_address': job_offer.job.jobsite.get_address(),
        'candidate_contact': job_offer.candidate_contact,
        'target_date_and_time': target_date_and_time,
        'master_company': master_company,
        'related_obj': job_offer,
        'related_objs': [job_offer.candidate_contact, job_offer.job]
    }

    sms_template = get_sms_template(company_id=master_company.id,
                                    candidate_contact_id=job_offer.candidate_contact.id,
                                    slug=tpl_id)
    sent_message = sms_interface.send_tpl(to_number=job_offer.candidate_contact.contact.phone_mobile,
                                          tpl_id=sms_template.id,
                                          check_reply=bool(action_sent), **data_dict)

    if action_sent and sent_message:
        related_query_name = hr_models.JobOfferSMS._meta.get_field(action_sent).related_query_name()
        cache.set(sent_message.pk, related_query_name, (sent_message.reply_timeout + 2) * 60)

        hr_models.JobOfferSMS.objects.create(
            job_offer=job_offer,
            **{action_sent: sent_message}
        )

        job_offer.scheduled_sms_datetime = None
        job_offer.save()


def send_or_schedule_job_offer_sms(job_offer_id, task=None, **kwargs):
    with transaction.atomic():
        try:
            job_offer = hr_models.JobOffer.objects.select_for_update().get(id=job_offer_id)
        except hr_models.JobOffer.DoesNotExist as e:
            logger.error(e)
        else:
            if job_offer.is_accepted():
                log_message = 'Job Offer %s already accepted'
                job_offer.scheduled_sms_datetime = None
                job_offer.save(update_fields=['scheduled_sms_datetime'])
                logger.info(log_message, str(job_offer_id))
                return

            if job_offer.is_cancelled():
                job_offer.scheduled_sms_datetime = None
                job_offer.status = hr_models.JobOffer.STATUS_CHOICES.undefined
                job_offer.save(update_fields=['scheduled_sms_datetime', 'status'])

            if job_offer.start_time_utc.date() > utc_now().date() \
                    and job_offer.has_timesheets_with_going_work_unset_or_timeout():
                eta_tz = job_offer.now_tz + timedelta(hours=2)
                if time(17, 0, 0, tzinfo=eta_tz.tzinfo) > eta_tz.timetz() > time(16, 0, 0, tzinfo=eta_tz.tzinfo):
                    eta_tz = datetime.combine(eta_tz.date(), time(16, 0, tzinfo=eta_tz.tzinfo))
                elif eta_tz.timetz() > time(17, 0, 0, tzinfo=eta_tz.tzinfo):
                    send_job_offer_sms(job_offer=job_offer, **kwargs)
                    return

                logger.info('JO SMS sending will be rescheduled for Job Offer: %s', str(job_offer_id))
                eta_utc = tz2utc(eta_tz)
                job_offer.scheduled_sms_datetime = eta_utc
                job_offer.save(update_fields=['scheduled_sms_datetime'])
                task.apply_async(args=[job_offer_id], eta=eta_utc)

            elif job_offer.start_time_utc.date() > utc_now().date() \
                    and job_offer.start_time_tz.timetz() >= time(16, 0, 0, tzinfo=job_offer.start_time_tz.tzinfo):
                eta_utc = job_offer.start_time_utc - timedelta(hours=8)
                job_offer.scheduled_sms_datetime = eta_utc
                job_offer.save(update_fields=['scheduled_sms_datetime'])
                task.apply_async(args=[job_offer_id], eta=eta_utc)
            else:
                send_job_offer_sms(job_offer=job_offer, **kwargs)


@shared_task(bind=True, queue='sms')
def send_jo_confirmation_sms(self, job_offer_id):
    send_or_schedule_job_offer_sms(job_offer_id,
                                   task=send_jo_confirmation_sms,
                                   tpl_id='job-offer-1st',
                                   action_sent='offer_sent_by_sms')


@shared_task(bind=True, queue='sms')
def send_recurring_jo_confirmation_sms(self, job_offer_id):
    send_or_schedule_job_offer_sms(job_offer_id,
                                   task=send_recurring_jo_confirmation_sms,
                                   tpl_id='job-offer-recurring',
                                   action_sent='offer_sent_by_sms')


def send_job_offer_sms_notification(jo_id, tpl_id, recipient):
    try:
        sms_interface = get_sms_service()
    except ImportError:
        logger.exception('Cannot load SMS service')
        return

    with transaction.atomic():
        try:
            job_offer = hr_models.JobOffer.objects.get(pk=jo_id)
            job = job_offer.job
        except hr_models.JobOffer.DoesNotExist as e:
            logger.error(e)
            logger.info('SMS sending will not be proceed for job offer: {}'.format(jo_id))
        else:
            recipients = {
                'candidate_contact': job_offer.candidate_contact,
                'supervisor': job.jobsite.primary_contact
            }
            data_dict = dict(
                recipients,
                job=job,
                target_date_and_time=formats.date_format(job_offer.start_time_tz, settings.DATETIME_FORMAT),
                related_obj=job_offer,
                related_objs=[job_offer.candidate_contact, job_offer.job]
            )

            master_company = job_offer.shift.date.job.jobsite.master_company

            sms_template = get_sms_template(company_id=master_company.id,
                                            candidate_contact_id=job_offer.candidate_contact.id,
                                            slug=tpl_id)
            sms_interface.send_tpl(to_number=recipients.get(recipient),
                                   tpl_id=sms_template.id,
                                   check_reply=False,
                                   **data_dict)


@app.task()
def send_job_offer_cancelled_sms(jo_id):
    """
    Send cancellation job offer sms.

    :param jo_id: UUID of job offer
    :return: None
    """

    send_job_offer_sms_notification(jo_id, 'candidate-jo-cancelled', 'candidate_contact')


@app.task()
def send_job_offer_cancelled_lt_one_hour_sms(jo_id):
    """
    Send cancellation job offer sms less than 1h.

    :param jo_id: UUID of job offer
    :return: None
    """

    send_job_offer_sms_notification(jo_id, 'candidate-jo-cancelled-1-hrs', 'candidate_contact')


@app.task(bind=True, queue='sms')
def send_placement_rejection_sms(self, job_offer_id):
    from r3sourcer.apps.sms_interface.models import SMSRelatedObject

    with transaction.atomic():
        job_offer = hr_models.JobOffer.objects.get(pk=job_offer_id)
        f_data = {
            'sms__template__slug': 'job-offer-rejection',
            'content_type': ContentType.objects.get_for_model(hr_models.JobOffer),
            'object_id': job_offer_id
        }
        if not SMSRelatedObject.objects.select_for_update().filter(**f_data).exists():
            send_job_offer_sms(job_offer, tpl_id='job-offer-rejection')


@shared_task
def generate_invoice(timesheet_id, recreate=False):
    """
    Generates new or updates existing invoice. Accepts regular(customer) company.
    """
    try:
        timesheet = hr_models.TimeSheet.objects.get(id=timesheet_id)
    except hr_models.TimeSheet.DoesNotExist:
        return

    company = timesheet.regular_company

    if company.type == core_models.Company.COMPANY_TYPES.master:
        return

    # TODO: Remove this import after fix import logic
    invoice_rule = utils.get_invoice_rule(company)
    date_from, date_to = utils.get_invoice_dates(invoice_rule, timesheet)
    invoice = utils.get_invoice(company, date_from, date_to, timesheet, invoice_rule)
    if invoice:
        deny_conditions = (
            invoice.is_paid,
            invoice.approved,
            invoice.sync_status in (
                core_models.Invoice.SYNC_STATUS_CHOICES.sync_scheduled,
                core_models.Invoice.SYNC_STATUS_CHOICES.syncing,
                core_models.Invoice.SYNC_STATUS_CHOICES.synced,
            )
        )

        if True in deny_conditions:
            return

    from r3sourcer.apps.hr.payment.invoices import InvoiceService
    service = InvoiceService()
    service.generate_invoice(date_from,
                             date_to,
                             company=company,
                             invoice=invoice,
                             recreate=recreate,
                             invoice_rule=invoice_rule)


@app.task(bind=True, queue='sms')
def process_time_sheet_log_and_send_notifications(self, time_sheet_id, event):
    """
    Send time sheet log sms notification.

    :param time_sheet_id: UUID TimeSheet instance
    :param event: str [SHIFT_ENDING, SUPERVISOR_DECLINED]
    :return:
    """
    events_dict = {
        SHIFT_ENDING: {
            'sms_tpl': 'candidate-timesheet-hours',
            'sms_old_tpl': 'candidate-timesheet-hours-old',
            'email_subject': _('Please fill time sheet'),
            'email_text': _('Please fill time sheet'),
            'email_tpl': 'candidate-timesheet-hours',
            'email_old_tpl': 'candidate-timesheet-hours-old',
            'delta_hours': 1,
        },
        SUPERVISOR_DECLINED: {
            'sms_tpl': 'candidate-timesheet-agree',
            'email_subject': _('Your time sheet was declined'),
            'email_text': _('Your time sheet was declined'),
            'email_tpl': '',
        },
    }

    try:
        time_sheet = hr_models.TimeSheet.objects.get(id=time_sheet_id)
    except hr_models.TimeSheet.DoesNotExist as e:
        logger.error(e)
    else:
        candidate = time_sheet.candidate_contact
        contacts = {
            'candidate_contact': candidate,
            'company_contact': time_sheet.supervisor
        }
        with transaction.atomic():
            site_url = core_companies_utils.get_site_url(user=contacts['candidate_contact'].contact.user)
            data_dict = dict(
                supervisor=contacts['company_contact'],
                candidate_contact=contacts['candidate_contact'],
                site_url=site_url,
                get_fill_time_sheet_url="%s/hr/timesheets-candidate" % site_url,
                get_supervisor_redirect_url="%s/hr/timesheets/unapproved" % site_url,
                get_supervisor_sign_url="%s/hr/timesheets/unapproved" % site_url,
                shift_start_date=formats.date_format(time_sheet.shift_started_at_tz, settings.DATETIME_FORMAT),
                shift_end_date=formats.date_format(time_sheet.shift_ended_at_tz.date(), settings.DATE_FORMAT),
                related_obj=time_sheet,
            )

            if event == SUPERVISOR_DECLINED:
                if time_sheet.break_started_at and time_sheet.break_ended_at:
                    break_delta = time_sheet.break_ended_at - time_sheet.break_started_at
                    break_str = format_timedelta(break_delta)
                else:
                    break_str = ''
                    break_delta = timedelta()

                worked_str = format_timedelta(time_sheet.shift_ended_at - time_sheet.shift_started_at - break_delta)

                data_dict.update(
                    shift_start_date=formats.date_format(time_sheet.shift_started_at_tz, settings.DATE_FORMAT),
                    shift_start_time=formats.time_format(time_sheet.shift_started_at_tz.time(), settings.TIME_FORMAT),
                    shift_end_time=formats.time_format(time_sheet.shift_ended_at_tz.time(), settings.TIME_FORMAT),
                    shift_break_hours=break_str,
                    shift_worked_hours=worked_str,
                    supervisor_timeout=format_timedelta(timedelta(seconds=settings.SUPERVISOR_DECLINE_TIMEOUT))
                )

                time_sheet.candidate_submitted_at = None
                time_sheet.save(update_fields=['candidate_submitted_at'])

                autoconfirm_rejected_timesheet.apply_async(
                    args=[time_sheet_id], countdown=settings.SUPERVISOR_DECLINE_TIMEOUT
                )

            if event == SHIFT_ENDING:
                recipient = time_sheet.candidate_contact

                sign_navigation = core_models.ExtranetNavigation.objects.get(id=124)
                role = recipient.contact.user.role.get(name=core_models.Role.ROLE_NAMES.candidate)
                extranet_login = TokenLogin.objects.create(
                    contact=recipient.contact,
                    redirect_to='{}{}/submit'.format(sign_navigation.url, time_sheet_id),
                    role=role
                )

                site_url = core_companies_utils.get_site_url(user=recipient.contact.user)
                data_dict.update({
                    'get_fill_time_sheet_url': "%s%s" % (site_url, extranet_login.auth_url),
                    'related_objs': [extranet_login],
                })
            else:
                recipient = time_sheet.supervisor

            master_company = core_companies_utils.get_site_master_company(user=candidate.contact.user)
            if candidate.message_by_sms:
                try:
                    sms_interface = get_sms_service()
                except ImportError:
                    logger.exception('Cannot load SMS service')
                    return

                sms_tpl = events_dict[event]['sms_tpl']
                if time_sheet.shift_ended_at.date() != utc_now().date():
                    sms_tpl = events_dict[event].get('sms_old_tpl', sms_tpl)

                sms_template = get_sms_template(company_id=master_company.id,
                                                candidate_contact_id=recipient.contact.candidate_contacts.id,
                                                slug=sms_tpl)
                sms_interface.send_tpl(to_number=recipient.contact.phone_mobile,
                                       tpl_id=sms_template.id,
                                       check_reply=False,
                                       **data_dict)

            if candidate.message_by_email:
                try:
                    email_interface = get_email_service()
                except ImportError:
                    logger.exception('Cannot load SMS service')
                    return

                email_tpl = events_dict[event]['email_tpl']
                if time_sheet.shift_ended_at.date() != utc_now().date():
                    email_tpl = events_dict[event].get('email_old_tpl', email_tpl)

                if not email_tpl:
                    return

                email_interface.send_tpl(recipient.contact.email, master_company, tpl_name=email_tpl, **data_dict)


@app.task(bind=True, queue='sms')
def autoconfirm_rejected_timesheet(self, time_sheet_id):
    try:
        time_sheet = hr_models.TimeSheet.objects.get(id=time_sheet_id)
    except hr_models.TimeSheet.DoesNotExist as e:
        logger.error(e)
    else:
        if time_sheet.candidate_submitted_at is None:
            time_sheet.candidate_submitted_at = utc_now()
            time_sheet.save(update_fields=['candidate_submitted_at'])


def send_supervisor_timesheet_message(
    supervisor, should_send_sms, should_send_email, sms_tpl, email_tpl=None, related_timesheets=None, **kwargs
):
    email_tpl = email_tpl or sms_tpl

    with transaction.atomic():
        sign_navigation = core_models.ExtranetNavigation.objects.get(id=119)
        role = supervisor.contact.user.role.filter(name=core_models.Role.ROLE_NAMES.client).first()
        if not role:
            role = supervisor.contact.user.role.filter(name=core_models.Role.ROLE_NAMES.manager).first()
        new_url_for_redirect = sign_navigation.url[:-1]

        extranet_login = TokenLogin.objects.create(
            contact=supervisor.contact,
            redirect_to=new_url_for_redirect,
            role=role
        )

        company_rel = supervisor.relationships.all().first()
        if company_rel:
            primary_contact = company_rel.company_contact or company_rel.company.primary_contact

        site_url = core_companies_utils.get_site_url(user=supervisor.contact.user)
        data_dict = dict(
            supervisor=supervisor,
            portfolio_manager=primary_contact,
            get_url="%s%s" % (site_url, extranet_login.auth_url),
            site_url=site_url,
            related_obj=supervisor,
            related_objs=[extranet_login],
        )
        data_dict['related_objs'].extend(related_timesheets or [])
        data_dict.update(kwargs)

        master_company = core_companies_utils.get_site_master_company(user=supervisor.contact.user)
        if should_send_sms and supervisor.contact.phone_mobile:
            try:
                sms_interface = get_sms_service()
            except ImportError:
                logger.exception('Cannot load SMS service')
                return

            sms_template = get_sms_template(company_id=master_company.id,
                                            candidate_contact_id=supervisor.contact.candidate_contacts.id,
                                            slug=sms_tpl)

            sms_interface.send_tpl(to_number=supervisor.contact.phone_mobile,
                                   tpl_id=sms_template.id,
                                   check_reply=False,
                                   **data_dict)

        if should_send_email:
            try:
                email_interface = get_email_service()
            except ImportError:
                logger.exception('Cannot load SMS service')
                return

            email_interface.send_tpl(supervisor.contact.email, master_company, tpl_name=email_tpl, **data_dict)


@app.task(bind=True, queue='sms')
def send_supervisor_timesheet_sign(self, supervisor_id, timesheet_id, force=False):
    try:
        supervisor = core_models.CompanyContact.objects.get(pk=supervisor_id)
    except core_models.CompanyContact.DoesNotExist:
        return

    try:
        time_sheet = hr_models.TimeSheet.objects.get(pk=timesheet_id)
    except hr_models.TimeSheet.DoesNotExist:
        return
    now_tz = time_sheet.now_tz
    now_utc = time_sheet.now_utc
    today_tz = now_tz.date()
    today_utc = now_utc.date()
    sms_tpl = 'supervisor-timesheet-sign'
    email_tpl = 'supervisor-timesheet-sign'

    if force:
        send_supervisor_timesheet_message(supervisor, True, True, sms_tpl, email_tpl,
                                          related_timesheets=[time_sheet])
        return

    should_send_sms = False
    if supervisor.message_by_sms:
        if not SMSMessage.objects.filter(
                  to_number=supervisor.contact.phone_mobile,
                  template__slug=sms_tpl,
                  sent_at__date=today_utc,
               ).exists():
            should_send_sms = True

    should_send_email = False
    if supervisor.message_by_email:
        if not EmailMessage.objects.filter(
                   to_addresses=supervisor.contact.email,
                   template__slug=email_tpl,
                   sent_at__date=today_utc).exists():
            should_send_email = True

    if not should_send_email and not should_send_sms:
        return

    if hr_models.TimeSheet.objects.filter(
            shift_ended_at__date=today_utc,
            going_to_work_confirmation=True,
            supervisor=supervisor).exists():

        today_shift_end = hr_models.TimeSheet.objects.filter(
            shift_ended_at__date=today_utc,
            going_to_work_confirmation=True,
            supervisor=supervisor
        ).latest('shift_ended_at').shift_ended_at

        timesheets = hr_models.TimeSheet.objects.filter(
            shift_ended_at__date=today_utc,
            shift_ended_at__lte=today_shift_end,
            going_to_work_confirmation=True,
            supervisor=supervisor
        )

        not_signed_timesheets = timesheets.filter(
            candidate_submitted_at__isnull=True,
            supervisor=supervisor
        )

        if not_signed_timesheets.exists():
            return

        signed_time_sheets = timesheets.filter(
            candidate_submitted_at__isnull=False,
            supervisor=supervisor,
        )

        signed_timesheets_started = signed_time_sheets.order_by(
            'shift_started_at',
        ).values_list(
            'shift_started_at',
            flat=True
        ).distinct()
        signed_timesheets_started = list(signed_timesheets_started)
        related_timesheets = list(signed_time_sheets)

        if time_sheet.shift_started_at not in signed_timesheets_started:
            signed_timesheets_started.append(time_sheet.shift_started_at)
            related_timesheets.append(time_sheet)

        if not signed_timesheets_started:
            return

        send_supervisor_timesheet_message(
            supervisor, should_send_sms, should_send_email, sms_tpl, email_tpl,
            related_timesheets=related_timesheets
        )

        eta = now_tz + timedelta(hours=4)
        is_today_reminder = True
        if eta.time() > time(19, 0):
            is_today_reminder = False
            eta = now_tz.replace(hour=19, minute=0, second=0)
        elif eta.time() < time(7, 0) or eta.date() > today_tz:
            eta = eta.replace(hour=7, minute=0, second=0)

        if eta.weekday() in range(5) and not core_models.PublicHoliday.is_holiday(eta.date()):
            utc_eta = tz2utc(eta)
            send_supervisor_timesheet_sign_reminder.apply_async(args=[supervisor_id, is_today_reminder], eta=utc_eta)


@app.task(bind=True, queue='sms')
@one_sms_task_at_the_same_time
def send_supervisor_timesheet_sign_reminder(self, supervisor_id, is_today):
    today = date.today()
    if not is_today:
        today -= timedelta(days=1)

    try:
        supervisor = core_models.CompanyContact.objects.get(
            id=supervisor_id,
            timesheet_reminder=True
        )
    except core_models.CompanyContact.DoesNotExist:
        return

    timesheets = hr_models.TimeSheet.objects.filter(
        shift_ended_at__date=today,
        going_to_work_confirmation=True,
        candidate_submitted_at__isnull=False,
        supervisor_approved_at__isnull=True,
        supervisor=supervisor
    )

    if timesheets.exists():
        send_supervisor_timesheet_message(
            supervisor, supervisor.message_by_sms, supervisor.message_by_email, 'supervisor-timesheet-sign-reminder',
            related_timesheets=timesheets
        )


@shared_task
def check_unpaid_invoices():
    master_companies = core_models.Company.objects.filter(provider_invoices__is_paid=False).distinct()

    for company in master_companies:
        unpaid_invoices = core_models.Invoice.objects.filter(provider_company=company, is_paid=False)
        date_from = unpaid_invoices.order_by('-date')[0].date - timedelta(days=32)
        client = get_myob_client(company.id)
        initialized = client.init_api(timeout=True)

        if not initialized:
            continue

        params = {"$filter": "Status eq 'Closed' and Date gt datetime'%s'" % date_from.strftime('%Y-%m-%d')}
        invoices = client.api.Sale.Invoice.Service.get(params=params)['Items']
        invoice_numbers = [x['Number'] for x in invoices]
        closed_invoices = core_models.Invoice.objects.filter(is_paid=False, number__in=invoice_numbers)
        closed_invoices.update(is_paid=True)


def send_timesheet_sms(timesheet_id, job_offer_id, sms_tpl, recipient, needs_target_dt=False):
    with transaction.atomic():
        try:
            timesheet = hr_models.TimeSheet.objects.get(pk=timesheet_id)
        except hr_models.TimeSheet.DoesNotExist as e:
            logger.error(e)
            logger.info('SMS sending will not be proceed for Timesheet: {}'.format(timesheet_id))
            return

        try:
            jo = hr_models.JobOffer.objects.get(pk=job_offer_id)
        except hr_models.JobOffer.DoesNotExist as e:
            logger.error(e)
            logger.info('SMS sending will not be proceed for JO: {}'.format(job_offer_id))
        else:
            master_company = timesheet.master_company
            data_dict = dict(
                job=jo.job,
                candidate_contact=jo.candidate_contact,
                supervisor=timesheet.supervisor,
                timesheet=timesheet,
                related_obj=jo.job,
                related_objs=[jo.candidate_contact, timesheet.supervisor, timesheet],
                master_company=master_company
            )
            if needs_target_dt:
                try:
                    target_date_and_time = formats.date_format(jo.start_time_tz, settings.DATETIME_FORMAT)
                except AttributeError as e:
                    logger.error(e)
                else:
                    data_dict.update({'target_date_and_time': target_date_and_time})

            try:
                recipient = operator.attrgetter(recipient)(timesheet)
            except AttributeError as e:
                logger.error(e)
                logger.info('Cannot get recipient for Timesheet: {}'.format(timesheet_id))
                return

            if recipient.contact.phone_mobile:
                try:
                    sms_interface = get_sms_service()
                except ImportError:
                    logger.exception('Cannot load SMS service')
                    return

                sms_template = get_sms_template(company_id=master_company.id,
                                                candidate_contact_id=recipient.contact.candidate_contacts.id,
                                                slug=sms_tpl)

                sms_interface.send_tpl(to_number=recipient.contact.phone_mobile,
                                       tpl_id=sms_template.id,
                                       check_reply=False,
                                       **data_dict)


@app.task(bind=True, queue='sms')
def send_placement_acceptance_sms(self, timesheet_id, job_offer_id):
    send_timesheet_sms(timesheet_id,
                       job_offer_id,
                       'job-offer-placement-confirmation',
                       'candidate_contact',
                       needs_target_dt=True
    )


@app.task(bind=True, queue='sms')
def send_going_to_work_sms(self, time_sheet_id):
    """
    Send morning check sms notification.
    Going to work sms message.

    :param time_sheet_id: UUID of TimeSheet instance
    :return:
    """
    action_sent = 'going_to_work_sent_sms'
    with transaction.atomic():
        try:
            time_sheet = hr_models.TimeSheet.objects.select_for_update().get(
                **{'pk': time_sheet_id, action_sent: None}
            )
        except hr_models.TimeSheet.DoesNotExist as e:
            logger.error(e)
        else:
            if (not time_sheet.master_company.company_settings.pre_shift_sms_enabled or
                    time_sheet.going_to_work_confirmation):
                return

            candidate_contact = time_sheet.job_offer.candidate_contact
            data_dict = dict(
                job=time_sheet.job_offer.job,
                candidate_contact=candidate_contact,
                target_date_and_time=formats.date_format(time_sheet.shift_started_at_tz, settings.DATETIME_FORMAT),
                related_obj=time_sheet,
                related_objs=[time_sheet.job_offer.job, candidate_contact],
            )
            check_reply = not time_sheet.going_to_work_confirmation

            try:
                sms_interface = get_sms_service()
            except ImportError:
                logger.exception('Cannot load SMS service')
                return

            sms_tpl ='candidate-going-to-work'
            sms_template = get_sms_template(company_id=time_sheet.master_company.id,
                                            candidate_contact_id=candidate_contact.id,
                                            slug=sms_tpl)
            sent_message = sms_interface.send_tpl(to_number=candidate_contact.contact.phone_mobile,
                                                  tpl_id=sms_template.id,
                                                  check_reply=check_reply,
                                                  **data_dict
            )

            if not sent_message:
                return

            setattr(time_sheet, action_sent, sent_message)
            time_sheet.update_status(False)
            time_sheet.save(update_fields=[action_sent, 'status'])
            related_query_name = hr_models.TimeSheet._meta.get_field(
                action_sent).related_query_name()
            cache.set(sent_message.pk, related_query_name, (sent_message.reply_timeout + 2) * 60)


def get_confirmation_string(job):
    dates = formats.date_format(job.work_start_date, settings.DATE_FORMAT)
    if job.shift_dates.exists():
        shift_dates_list = job.shift_dates.filter(
            shift_date__gte=date.today()
        ).order_by('shift_date').values_list('shift_date', flat=True)

        if len(shift_dates_list) > 0:
            # if year is the same removes year from the string
            if shift_dates_list[0].year == shift_dates_list[len(shift_dates_list) - 1].year:
                shift_dates = utils.format_dates_range(shift_dates_list)
            else:
                shift_dates = [
                    formats.date_format(fulldate.astimezone(job.tz), settings.DATE_FORMAT)
                    for fulldate in shift_dates_list
                ]

            dates = ', '.join(shift_dates)
        shift_date = job.shift_dates.filter(shift_date__gte=date.today()).order_by('shift_date').first()
        time = formats.time_format(shift_date.shifts.order_by('time').first().time)
    else:
        time = formats.date_format(job.default_shift_starting_time, settings.TIME_FORMAT)
    return _("{} {} for dates {}, shifts starting {}").format(job.workers, job.position, dates, time)


@app.task(bind=True, queue='sms')
def send_job_confirmation_sms(self, job_id):
    """
    Send sms for Job confirmation.

    :param self: Task instance
    :param job_id: UUID of Job
    :return: None
    """

    try:
        job = hr_models.Job.objects.get(id=job_id)
        jobsite = job.jobsite
        if not job.customer_representative.receive_job_confirmation_sms:
            logger.info("Client Representative %s should\'t receive job confirmation SMS", str(job.primary_contact))
            return
    except hr_models.Job.DoesNotExist:
        logger.warn('Job with id %s does not exists', str(job_id))
        return

    try:
        sms_interface = get_sms_service()
    except ImportError:
        logger.exception('Cannot load SMS service')
        return

    with transaction.atomic():
        confirmation_string = get_confirmation_string(job)

        sign_navigation = core_models.ExtranetNavigation.objects.get(id=110)
        role = job.customer_representative.contact.user.role.filter(name=core_models.Role.ROLE_NAMES.client).first()
        if not role:
            role = job.customer_representative.contact.user.role.filter(
                name=core_models.Role.ROLE_NAMES.manager
            ).first()

        extranet_login = TokenLogin.objects.create(
            contact=job.customer_representative.contact,
            redirect_to='{}{}/change/'.format(sign_navigation.url, job_id),
            role=role
        )
        site_url = core_companies_utils.get_site_url(user=job.customer_representative.contact.user)
        data_dict = dict(
            get_confirmation_string=confirmation_string,
            supervisor=job.customer_representative,
            jobsite=jobsite,
            portfolio_manager=job.provider_representative,
            auth_url="%s%s" % (site_url, extranet_login.auth_url),
            related_obj=job,
            related_objs=[job.customer_representative, jobsite, job.provider_representative, extranet_login],
        )
        master_company = jobsite.master_company
        sms_tpl = 'job-confirmed'
        sms_template = get_sms_template(company_id=master_company.id,
                                        candidate_contact_id=job.customer_representative.contact.candidate_contacts.id,
                                        slug=sms_tpl)
        sms_interface.send_tpl(to_number=job.customer_representative.contact.phone_mobile,
                               tpl_id=sms_template.id,
                               check_reply=False,
                               **data_dict)


@app.task(bind=True, queue='hr')
def close_not_active_jobsites(self):
    not_active_delta = timedelta(seconds=settings.JOBSITE_NOT_ACTIVE_TIMEOUT)
    timeout_datetime = utc_now() - not_active_delta

    jobsites = hr_models.Jobsite.objects.annotate(
        active_ts_sum=models.Sum(models.Case(
            models.When(
                models.Q(jobs__shift_dates__shift_date=timeout_datetime.date(),
                         jobs__shift_dates__shifts__time__gte=timeout_datetime.timetz()) |
                models.Q(jobs__shift_dates__shift_date__gt=timeout_datetime.date()),
                then=1
            ),
            default=0,
            output_field=models.IntegerField()
        ))
    ).filter(
        active_ts_sum=0, is_available=True
    ).distinct()

    for jobsite in jobsites:
        core_models.Note.objects.create(
            content_type=ContentType.objects.get_for_model(hr_models.Jobsite),
            object_id=jobsite.id,
            note="Jobsite is not active for more than {} days".format(
                not_active_delta.days
            )
        )

        jobsite.is_available = False
        jobsite.save(update_fields=['is_available'])


@shared_task
def auto_approve_timesheet(timesheet_id):
    hr_models.TimeSheet.objects.filter(
        id=timesheet_id,
        status=hr_models.TimeSheet.STATUS_CHOICES.modified
    ).update(
        status=hr_models.TimeSheet.STATUS_CHOICES.approved,
        supervisor_approved_at=utc_now())


def get_file_from_str(str):
    from io import BytesIO
    import weasyprint
    pdf = weasyprint.HTML(string=str)
    pdf_file = BytesIO()
    pdf_file.write(pdf.write_pdf())
    pdf_file.seek(0)

    return pdf_file


def timesheets_group_by_job_site(timesheets):
    from itertools import groupby
    for grouper, group in groupby(timesheets, key=lambda x: x.job_offer.shift.date.job.jobsite):
        yield grouper, list(group)


def get_price_list_rate(skill, customer_company):
    price_list_rate = PriceListRate.objects.filter(
        skill=skill,
        price_list__company=customer_company,
    ).last()

    return price_list_rate


def get_value_for_rate_type(coeffs_hours, rate_type):
    for coeff in coeffs_hours:
        rate = coeff['coefficient']
        if rate is None:
            return 'base'
        try:
            rate = rate.name.lower()
        except Exception:
            pass

        if rate_type in rate:
            return coeff['hours']
    return timedelta()


def generate_pdf(timesheet_ids, request=None, master_company=None):
    template = get_template('timesheet/timesheet.html')
    timesheets = hr_models.TimeSheet.objects.filter(id__in=timesheet_ids).order_by(
        'job_offer__shift__date__job__jobsite', 'shift_started_at')
    domain = core_companies_utils.get_site_url(user=request and request.user, master_company=master_company)
    coefficient_service = CoefficientService()

    for timesheet in timesheets:
        jobsite = timesheet.job_offer.job.jobsite
        industry = jobsite.industry
        worked_hours = calc_worked_delta(timesheet)
        coeffs_hours = coefficient_service.calc(timesheet.master_company,
                                                industry,
                                                RateCoefficientModifier.TYPE_CHOICES.candidate,
                                                timesheet.shift_started_at_tz,
                                                worked_hours,
                                                break_started=timesheet.break_started_at_tz,
                                                break_ended=timesheet.break_ended_at_tz)
        timesheet.coeffs_hours = coeffs_hours
        name_mapping = {'base': 'base', '1.5': 'c_1_5x', '2': 'c_2x', 'meal': 'meal', 'travel': 'travel'}

        for rate_type, value in name_mapping.items():
            setattr(timesheet, value, get_value_for_rate_type(coeffs_hours, rate_type))
        if str(timesheet.travel) == '1:00:00':
            timesheet.travel = 1
        else:
            timesheet.travel = 0
        if str(timesheet.meal) == '1:00:00':
            timesheet.meal = 1
        else:
            timesheet.meal = 0

    context = {
        'timesheets': timesheets_group_by_job_site(timesheets),
        'request': request,
        'domain': domain,
    }

    pdf_file = get_file_from_str(str(template.render(context)))
    folder, created = Folder.objects.get_or_create(
        parent=timesheets[0].master_company.files,
        name='timesheet',
    )
    file_name = 'timesheet_{}_{}_{}.pdf'.format(
        str(timesheets[0].id),
        date_format(timesheets[0].shift_started_at_tz, 'Y_m_d'),
        date_format(timesheets[0].shift_ended_at_tz, 'Y_m_d')
    )
    file_obj, created = File.objects.get_or_create(
        folder=folder,
        name=file_name,
        file=ContentFile(pdf_file.read(), name=file_name)
    )

    return file_obj


@shared_task
def send_invoice_email(invoice_id):
    try:
        invoice = core_models.Invoice.objects.get(pk=invoice_id)
    except core_models.Invoice.DoesNotExist:
        logger.warn('Invoice with id=%s does not exist', invoice_id)
        return

    master_company = invoice.provider_company
    client_company = invoice.customer_company

    try:
        email_interface = get_email_service()
    except ImportError:
        logger.exception('Cannot load SMS service')
        return

    try:
        pdf_file_obj = File.objects.get(
            name='invoice_{}_{}.pdf'.format(
                invoice.number,
                date_format(invoice.date, 'Y_m_d')
            )
        )
    except ObjectDoesNotExist:
        rule = master_company.invoice_rules.first()
        show_candidate = rule.show_candidate_name if rule else False
        from r3sourcer.apps.hr.payment.invoices import InvoiceService
        pdf_file_obj = InvoiceService.generate_pdf(invoice, show_candidate)

    timesheet_ids = invoice.invoice_lines.values_list('timesheet_id', flat=True).distinct()
    timesheets_pdf = generate_pdf(timesheet_ids, master_company=master_company)

    context = {
        'files': [pdf_file_obj, timesheets_pdf],
        'master_company': master_company.name,
        'master_company_contact': str(invoice.provider_representative),
        'client': client_company.name,
    }
    email_interface.send_tpl(client_company.billing_email, master_company, tpl_name='client-invoice', **context)


@shared_task
def generate_invoices():
    for company in core_models.Company.objects.all():
        today = company.today_tz
        invoice_rules = core_models.InvoiceRule.objects.filter(
            models.Q(period=core_models.InvoiceRule.PERIOD_CHOICES.weekly,
                     period_zero_reference=today.isoweekday()) |
            models.Q(period=core_models.InvoiceRule.PERIOD_CHOICES.monthly,
                     period_zero_reference=today.day) |
            models.Q(period=core_models.InvoiceRule.PERIOD_CHOICES.daily),
            company=company,
        )

        # TODO: remove this inline import after fix import logic
        from r3sourcer.apps.hr.payment.invoices import InvoiceService
        service = InvoiceService()

        for invoice_rule in invoice_rules:
            if invoice_rule.period == core_models.InvoiceRule.PERIOD_CHOICES.weekly:
                date_to = today - timedelta(today.isoweekday())
                date_from = date_to - timedelta(days=6)
            elif invoice_rule.period == core_models.InvoiceRule.PERIOD_CHOICES.monthly:
                date_to = today - timedelta(today.day)
                date_from = date_to.replace(day=1)
            else:
                date_to = today
                date_from = today - timedelta(days=1)

            existing_invoices = core_models.Invoice.objects.filter(
                models.Q(provider_company=company) |
                models.Q(customer_company=company),
                invoice_lines__date__gte=date2utc_date(date_from, company.tz),
                invoice_lines__date__lte=date2utc_date(date_to, company.tz),

            )

            if not existing_invoices:
                service.generate_invoice(date_from,
                                         date_to,
                                         company=company,
                                         invoice_rule=invoice_rule)

        fortnightly = core_models.InvoiceRule.objects.filter(
            period=core_models.InvoiceRule.PERIOD_CHOICES.fortnightly,
            company=company,
        )

        for invoice_rule in fortnightly:
            if invoice_rule.last_invoice_created:
                last_invoice_date = invoice_rule.last_invoice_created
                date_from = last_invoice_date - timedelta(days=invoice_rule.period_zero_reference)
                date_to = date_from + timedelta(14)
            else:
                date_to = today - timedelta(invoice_rule.period_zero_reference)
                date_from = date_to - timedelta(days=14)

            if date_from.isoweekday() != 1 or today != date_to + timedelta(days=invoice_rule.period_zero_reference):
                continue

            service.generate_invoice(date_from,
                                     date_to,
                                     company=company,
                                     invoice_rule=invoice_rule)
