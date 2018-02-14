from datetime import timedelta, date, time, datetime
from calendar import monthrange

from celery import shared_task
from celery.utils.log import get_task_logger

from r3sourcer.celeryapp import app

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone, formats
from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.core.models import Company, InvoiceRule, Invoice, Contact
from r3sourcer.apps.core.tasks import one_sms_task_at_the_same_time
from r3sourcer.apps.hr import models as hr_models
from r3sourcer.apps.hr.payment import InvoiceService, PayslipService
from r3sourcer.apps.hr.utils.utils import get_invoice_rule, get_payslip_rule, calculate_distances_for_jobsite
from r3sourcer.apps.pricing.utils.utils import format_timedelta
from r3sourcer.apps.sms_interface.utils import get_sms_service
from r3sourcer.apps.email_interface.utils import get_email_service


logger = get_task_logger(__name__)

GOING_TO_WORK, SHIFT_ENDING, RECRUITEE_SUBMITTED, SUPERVISOR_DECLINED = range(7)
SITE_URL = settings.SITE_URL


@shared_task
def prepare_invoices():
    service = InvoiceService()
    now = timezone.localtime(timezone.now())

    for company in Company.objects.filter(type='regular'):
        invoice_rule = get_invoice_rule(company)

        if not invoice_rule:
            continue

        if invoice_rule.period == InvoiceRule.PERIOD_CHOICES.monthly and \
                invoice_rule.period_zero_reference == now.day:
            if now.month == 1:
                year = now.year - 1
                month = 12
            else:
                year = now.year
                month = month - 1

            last_day = monthrange(year, month)
            day = now.day if now.day <= last_day else last_day

            from_date = date(year, month, day)
        elif invoice_rule.period == InvoiceRule.PERIOD_CHOICES.fortnightly:
            from_date = (now - timedelta(days=14)).date()
        elif invoice_rule.period == InvoiceRule.PERIOD_CHOICES.weekly:
            from_date = (now - timedelta(days=7)).date()
        elif invoice_rule.period == InvoiceRule.PERIOD_CHOICES.daily:
            from_date = (now - timedelta(days=1)).date()
        else:
            from_date = None

        if from_date:
            existing_invoice = Invoice.objects.filter(
                company=company,
                date__gte=from_date
            )
            if existing_invoice.exists():
                existing_invoice = existing_invoice.latest('date')
                from_date = existing_invoice.date + timedelta(days=1)

            service.prepare(company, from_date)


@shared_task
def prepare_payslips():
    service = PayslipService()
    now = timezone.localtime(timezone.now())

    for company in Company.objects.all():
        payslip_rule = get_payslip_rule(company)

        if not payslip_rule:
            continue

        to_date = now.date()
        if payslip_rule.period == hr_models.PayslipRule.PERIOD_CHOICES.monthly and \
                payslip_rule.period_zero_reference == now.day:
            if now.month == 1:
                year = now.year - 1
                month = 12
            else:
                year = now.year
                month = month - 1

            last_day = monthrange(year, month)
            day = now.day if now.day <= last_day else last_day

            from_date = date(year, month, day)
        elif payslip_rule.period == hr_models.PayslipRule.PERIOD_CHOICES.fortnightly:
            from_date = (now - timedelta(days=14)).date()
        elif payslip_rule.period == hr_models.PayslipRule.PERIOD_CHOICES.weekly:
            from_date = (now - timedelta(days=7)).date()
        elif payslip_rule.period == hr_models.PayslipRule.PERIOD_CHOICES.daily:
            from_date = (now - timedelta(days=1)).date()
        else:
            from_date = None

        if from_date:
            existing_payslip = hr_models.Payslip.objects.filter(
                company=company,
                from_date__gte=from_date,
            )
            if existing_payslip.exists():
                existing_payslip = existing_payslip.latest('date')
                from_date = existing_payslip.from_date + timedelta(days=1)

            service.prepare(company, from_date, to_date)


@shared_task
def update_all_distances():

    all_calculated_jobsites = hr_models.Jobsite.objects.filter(
        id__in=hr_models.ContactJobsiteDistanceCache.objects.filter(
            updated_at__isnull=True
        ).values('jobsite')
    )

    for jobsite in all_calculated_jobsites:
        if not (jobsite.latitude == 0 and jobsite.longitude == 0):
            contacts = Contact.objects.filter(distance_caches__jobsite=jobsite)
            if not calculate_distances_for_jobsite(contacts, jobsite):
                break


def send_vacancy_offer_sms(vacancy_offer, tpl_id, action_sent=None):
    """
    Send vacancy offer sms with specific template.

    :param vacancy_offer: VacancyOffer
    :param tpl_id: SMSTemplate UUID
    :param action_sent: str Model field for waiting sms reply
    :return:
    """
    try:
        sms_interface = get_sms_service()
    except ImportError:
        logger.exception('Cannot load SMS service')
        return

    target_date_and_time = formats.date_format(vacancy_offer.start_time, settings.DATETIME_FORMAT)

    now = timezone.localtime(timezone.now())
    if now >= timezone.localtime(vacancy_offer.start_time):
        target_date_and_time = "ASAP"

    data_dict = {
        'vacancy_offer': vacancy_offer,
        'vacancy': vacancy_offer.vacancy,
        'jobsite_address': vacancy_offer.vacancy.jobsite.get_address(),
        'candidate_contact': vacancy_offer.candidate_contact,
        'target_date_and_time': target_date_and_time,
        'related_obj': vacancy_offer,
        'related_objs': [vacancy_offer.candidate_contact, vacancy_offer.vacancy]
    }
    sent_message = sms_interface.send_tpl(
        vacancy_offer.candidate_contact.contact.phone_mobile, tpl_id, check_reply=bool(action_sent), **data_dict
    )

    if action_sent:
        related_query_name = hr_models.VacancyOffer._meta.get_field(action_sent).related_query_name()
        cache.set(sent_message.pk, related_query_name, (sent_message.reply_timeout + 2) * 60)

        setattr(vacancy_offer, action_sent, sent_message)
        vacancy_offer.scheduled_sms_datetime = None
        vacancy_offer.save()


def send_or_schedule_vacancy_offer_sms(vacancy_offer_id, task=None, **kwargs):
    action_sent = kwargs.get('action_sent')

    with transaction.atomic():
        try:
            vacancy_offer = hr_models.VacancyOffer.objects.select_for_update().get(
                **{'pk': vacancy_offer_id, action_sent: None}
            )
        except hr_models.VacancyOffer.DoesNotExist as e:
            logger.error(e)
        else:
            log_message = None
            if vacancy_offer.is_accepted():
                log_message = 'Vacancy Offer %s already accepted'
            elif vacancy_offer.is_cancelled():
                log_message = 'Vacancy Offer %s already cancelled'

            if log_message:
                vacancy_offer.scheduled_sms_datetime = None
                vacancy_offer.save(update_fields=['scheduled_sms_datetime'])
                logger.info(log_message, str(vacancy_offer_id))
                return

            now = timezone.localtime(timezone.now())
            today = now.date()
            vo_target_datetime = vacancy_offer.start_time
            vo_target_date = vo_target_datetime.date()
            vo_tz = vo_target_datetime.tzinfo
            if vo_target_date > today and vacancy_offer.has_timesheets_with_going_work_unset_or_timeout():
                eta = now + timedelta(hours=2)
                if time(17, 0, 0, tzinfo=eta.tzinfo) > eta.timetz() > time(16, 0, 0, tzinfo=eta.tzinfo):
                    eta = datetime.combine(eta.date(), time(16, 0, tzinfo=eta.tzinfo))
                elif eta.timetz() > time(17, 0, 0, tzinfo=eta.tzinfo):
                    send_vacancy_offer_sms(vacancy_offer=vacancy_offer, **kwargs)
                    return

                if task:
                    task.apply_async(args=[vacancy_offer_id], eta=eta)

                    vacancy_offer.scheduled_sms_datetime = eta
                    vacancy_offer.save(update_fields=['scheduled_sms_datetime'])

                    logger.info('VO SMS sending will be rescheduled for Vacancy Offer: %s', str(vacancy_offer_id))
            elif vo_target_date > today and vo_target_datetime.timetz() >= time(16, 0, 0, tzinfo=vo_tz):
                task.apply_async(args=[vacancy_offer_id], eta=vo_target_datetime - timedelta(hours=8))
                vacancy_offer.scheduled_sms_datetime = vo_target_datetime - timedelta(hours=8)
                vacancy_offer.save(update_fields=['scheduled_sms_datetime'])
            else:
                send_vacancy_offer_sms(vacancy_offer=vacancy_offer, **kwargs)


@shared_task(bind=True)
@one_sms_task_at_the_same_time
def send_vo_confirmation_sms(self, vacancy_offer_id):
    send_or_schedule_vacancy_offer_sms(
        vacancy_offer_id, send_vo_confirmation_sms,
        tpl_id='vacancy-offer-1st', action_sent='offer_sent_by_sms'
    )


@shared_task(bind=True)
@one_sms_task_at_the_same_time
def send_recurring_vo_confirmation_sms(self, vacancy_offer_id):
    send_or_schedule_vacancy_offer_sms(
        vacancy_offer_id, send_recurring_vo_confirmation_sms,
        tpl_id='vacancy-offer-recurring', action_sent='offer_sent_by_sms'
    )


def send_vacancy_offer_sms_notification(vo_id, tpl_id, recipient):
    try:
        sms_interface = get_sms_service()
    except ImportError:
        logger.exception('Cannot load SMS service')
        return

    with transaction.atomic():
        try:
            vacancy_offer = hr_models.VacancyOffer.objects.get(pk=vo_id)
            vacancy = vacancy_offer.vacancy
        except hr_models.VacancyOffer.DoesNotExist as e:
            logger.error(e)
            logger.info('SMS sending will not be proceed for vacancy offer: {}'.format(vo_id))
        else:
            recipients = {
                'candidate_contact': vacancy_offer.candidate_contact,
                'supervisor': vacancy.jobsite.primary_contact
            }
            data_dict = dict(
                recipients,
                vacancy=vacancy,
                target_date_and_time=formats.date_format(
                    timezone.localtime(vacancy_offer.target_date_and_time), settings.DATETIME_FORMAT
                ),
                related_obj=vacancy_offer,
                related_objs=[vacancy_offer.candidate_contact, vacancy_offer.vacancy]
            )

            sms_interface.send_tpl(
                recipients.get(recipient, None), tpl_id, check_reply=False, **data_dict
            )


@app.task()
def send_vacancy_offer_cancelled_sms(vo_id):
    """
    Send cancellation vacancy offer sms.

    :param vo_id: UUID of vacancy offer
    :return: None
    """

    send_vacancy_offer_sms_notification(vo_id, 'candidate-vo-cancelled', 'candidate_contact')


@app.task()
def send_vacancy_offer_cancelled_lt_one_hour_sms(vo_id):
    """
    Send cancellation vacancy offer sms less than 1h.

    :param vo_id: UUID of vacancy offer
    :return: None
    """

    send_vacancy_offer_sms_notification(vo_id, 'candidate-vo-cancelled-1-hrs', 'candidate_contact')


@app.task(bind=True)
@one_sms_task_at_the_same_time
def send_placement_rejection_sms(self, vacancy_offer_id):
    from r3sourcer.apps.sms_interface.models import SMSRelatedObject

    with transaction.atomic():
        vacancy_offer = hr_models.VacancyOffer.objects.get(pk=vacancy_offer_id)
        f_data = {
            'sms__template__slug': 'vacancy-offer-rejection',
            'object_model': ContentType.objects.get_for_model(hr_models.VacancyOffer),
            'object_id': vacancy_offer_id
        }
        if not SMSRelatedObject.objects.select_for_update().filter(**f_data).exists():
            send_vacancy_offer_sms(vacancy_offer, 'vacancy-offer-rejection')


@app.task(queue='sms')
def process_time_sheet_log_and_send_notifications(time_sheet_id, event):
    """
    Send time sheet log sms notification.

    :param time_sheet_id: UUID TimeSheet instance
    :param event: str [SHIFT_ENDING, RECRUITEE_SUBMITTED, SUPERVISOR_DECLINED]
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
        target_date_and_time = timezone.localtime(time_sheet.shift_started_at)
        end_date_and_time = timezone.localtime(time_sheet.shift_ended_at)
        contacts = {
            'candidate_contact': candidate,
            'company_contact': time_sheet.supervisor
        }

        with transaction.atomic():
            data_dict = dict(
                supervisor=contacts['client_contact'],
                candidate_contact=contacts['candidate_contact'],
                get_fill_time_sheet_url="%shr/timesheets" % SITE_URL,
                get_supervisor_redirect_url="%shr/timesheets" % SITE_URL,
                get_supervisor_sign_url="%shr/timesheets" % SITE_URL,
                shift_start_date=formats.date_format(target_date_and_time, settings.DATETIME_FORMAT),
                shift_end_date=formats.date_format(end_date_and_time.date(), settings.DATE_FORMAT),
                booking=time_sheet.booking,
                vacancy=time_sheet.booking.vacancy,
                related_obj=time_sheet,
            )

            if event == SUPERVISOR_DECLINED:
                end_date_and_time = timezone.localtime(time_sheet.shift_ended_at)

                if time_sheet.break_started_at and time_sheet.break_ended_at:
                    break_delta = time_sheet.break_ended_at - time_sheet.break_started_at
                    break_str = format_timedelta(break_delta)
                else:
                    break_str = ''
                    break_delta = timedelta()

                worked_str = format_timedelta(time_sheet.shift_ended_at - time_sheet.shift_started_at - break_delta)

                data_dict.update(
                    shift_start_date=formats.date_format(target_date_and_time, settings.DATE_FORMAT),
                    shift_start_time=formats.time_format(target_date_and_time.time(), settings.TIME_FORMAT),
                    shift_end_time=formats.time_format(end_date_and_time.time(), settings.TIME_FORMAT),
                    shift_break_hours=break_str,
                    shift_worked_hours=worked_str,
                    supervisor_timeout=format_timedelta(timedelta(seconds=settings.SUPERVISOR_DECLINE_TIMEOUT))
                )

                time_sheet.candidate_submitted_at = None
                time_sheet.save(update_fields=['candidate_submitted_at'])

                autoconfirm_rejected_timesheet.apply_async(
                    args=[time_sheet_id], countdown=settings.SUPERVISOR_DECLINE_TIMEOUT
                )

            today = date.today()

            if event == RECRUITEE_SUBMITTED:
                recipient = time_sheet.supervisor
            else:
                recipient = time_sheet.candidate_contact

            if candidate.by_sms:
                try:
                    sms_interface = get_sms_service()
                except ImportError:
                    logger.exception('Cannot load SMS service')
                    return

                sms_tpl = events_dict[event]['sms_tpl']
                if end_date_and_time.date() != today:
                    sms_tpl = events_dict[event].get('sms_old_tpl', sms_tpl)

                sms_interface.send_tpl(recipient.contact.phone_mobile, sms_tpl, check_reply=False, **data_dict)

            if candidate.by_email:
                try:
                    email_interface = get_email_service()
                except ImportError:
                    logger.exception('Cannot load SMS service')
                    return

                email_tpl = events_dict[event]['email_tpl']
                if end_date_and_time.date() != today:
                    email_tpl = events_dict[event].get('email_old_tpl', email_tpl)

                if not email_tpl:
                    return

                email_interface.send_tpl(recipient.contact.email, tpl_name=email_tpl, **data_dict)


@app.task(bind=True)
@one_sms_task_at_the_same_time
def autoconfirm_rejected_timesheet(self, time_sheet_id):
    try:
        time_sheet = hr_models.TimeSheet.objects.get(id=time_sheet_id)
    except hr_models.TimeSheet.DoesNotExist as e:
        logger.error(e)
    else:
        if time_sheet.candidate_submitted_at is None:
            time_sheet.candidate_submitted_at = timezone.now()
            time_sheet.save(update_fields=['candidate_submitted_at'])
