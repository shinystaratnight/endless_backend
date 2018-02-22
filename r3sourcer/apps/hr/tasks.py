from datetime import timedelta, date, time, datetime

from celery import shared_task
from celery.utils.log import get_task_logger

from r3sourcer.celeryapp import app

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone, formats
from django.utils.translation import ugettext_lazy as _

from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.tasks import one_sms_task_at_the_same_time
from r3sourcer.apps.email_interface.models import EmailMessage
from r3sourcer.apps.email_interface.utils import get_email_service
from r3sourcer.apps.hr import models as hr_models
from r3sourcer.apps.hr.payment import InvoiceService
from r3sourcer.apps.hr.utils import utils
from r3sourcer.apps.login.models import TokenLogin
from r3sourcer.apps.myob.api.wrapper import MYOBClient
from r3sourcer.apps.myob.models import MYOBCompanyFileToken
from r3sourcer.apps.pricing.utils.utils import format_timedelta
from r3sourcer.apps.sms_interface.models import SMSMessage
from r3sourcer.apps.sms_interface.utils import get_sms_service


logger = get_task_logger(__name__)

GOING_TO_WORK, SHIFT_ENDING, RECRUITEE_SUBMITTED, SUPERVISOR_DECLINED = range(4)
SITE_URL = settings.SITE_URL


@shared_task
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


@shared_task
def generate_invoice(timesheet):
    """
    Generates new or updates existing invoice. Accepts regular(customer) company.
    """
    company = timesheet.regular_company
    service = InvoiceService()
    invoice_rule = utils.get_invoice_rule(company)
    date_from, date_to = utils.get_invoice_dates(invoice_rule, timesheet)
    invoice = utils.get_invoice(company, date_from, date_to, timesheet)
    service.generate_invoice(date_from, date_to, company=company, invoice=invoice)


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
                supervisor=contacts['company_contact'],
                candidate_contact=contacts['candidate_contact'],
                site_url=SITE_URL,
                get_fill_time_sheet_url="%s/hr/timesheets-candidate" % SITE_URL,
                get_supervisor_redirect_url="%s/hr/timesheets/unapproved" % SITE_URL,
                get_supervisor_sign_url="%s/hr/timesheets/unapproved" % SITE_URL,
                shift_start_date=formats.date_format(target_date_and_time, settings.DATETIME_FORMAT),
                shift_end_date=formats.date_format(end_date_and_time.date(), settings.DATE_FORMAT),
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

            if event == SHIFT_ENDING:
                recipient = time_sheet.candidate_contact

                sign_navigation = core_models.ExtranetNavigation.objects.get(id=124)
                extranet_login = TokenLogin.objects.create(
                    contact=recipient.contact,
                    redirect_to='{}{}/submit/'.format(sign_navigation.url, time_sheet_id)
                )

                data_dict.update({
                    'get_fill_time_sheet_url': "%s%s" % (settings.SITE_URL, extranet_login.auth_url),
                    'related_objs': [extranet_login],
                })
            else:
                recipient = time_sheet.supervisor

            if candidate.message_by_sms:
                try:
                    sms_interface = get_sms_service()
                except ImportError:
                    logger.exception('Cannot load SMS service')
                    return

                sms_tpl = events_dict[event]['sms_tpl']
                if end_date_and_time.date() != today:
                    sms_tpl = events_dict[event].get('sms_old_tpl', sms_tpl)

                sms_interface.send_tpl(recipient.contact.phone_mobile, sms_tpl, check_reply=False, **data_dict)

            if candidate.message_by_email:
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


def send_supervisor_timesheet_message(
    supervisor, should_send_sms, should_send_email, sms_tpl, email_tpl=None, **kwargs
):
    email_tpl = email_tpl or sms_tpl

    with transaction.atomic():
        sign_navigation = core_models.ExtranetNavigation.objects.get(id=119)
        extranet_login = TokenLogin.objects.create(
            contact=supervisor.contact,
            redirect_to=sign_navigation.url
        )

        company_rel = supervisor.relationships.all().first()
        if company_rel:
            portfolio_manager = company_rel.company.manager

        data_dict = dict(
            supervisor=supervisor,
            portfolio_manager=portfolio_manager,
            get_url="%s%s" % (settings.SITE_URL, extranet_login.auth_url),
            site_url=settings.SITE_URL,
            related_obj=supervisor,
            related_objs=[extranet_login],
        )
        data_dict.update(kwargs)

        if should_send_sms and supervisor.contact.phone_mobile:
            try:
                sms_interface = get_sms_service()
            except ImportError:
                logger.exception('Cannot load SMS service')
                return

            sms_interface.send_tpl(supervisor.contact.phone_mobile, sms_tpl, check_reply=False, **data_dict)

        if should_send_email:
            try:
                email_interface = get_email_service()
            except ImportError:
                logger.exception('Cannot load SMS service')
                return

            email_interface.send_tpl(supervisor.contact.email, tpl_name=email_tpl, **data_dict)


@app.task(bind=True)
@one_sms_task_at_the_same_time
def send_supervisor_timesheet_sign(self, supervisor_id, timesheet_id):
    try:
        supervisor = core_models.CompanyContact.objects.get(id=supervisor_id)
    except core_models.CompanyContact.DoesNotExist:
        supervisor = None

    try:
        timesheet = hr_models.TimeSheet.objects.get(id=timesheet_id)
    except hr_models.TimeSheet.DoesNotExist:
        timesheet = None

    if not supervisor or not timesheet:
        return

    try:
        now = timezone.localtime(timezone.now())
        today = now.date()

        should_send_sms = False
        sms_tpl = 'supervisor-timesheet-sign'
        if supervisor.message_by_sms:
            if not SMSMessage.objects.filter(to_number=supervisor.contact.phone_mobile,
                                             template__slug=sms_tpl, sent_at__date=today).exists():
                should_send_sms = True

        should_send_email = False
        email_tpl = 'supervisor-timesheet-sign'
        if supervisor.message_by_email:
            if not EmailMessage.objects.filter(to_addresses=supervisor.contact.email,
                                               template__slug=email_tpl, sent_at__date=today).exists():
                should_send_email = True

        if not should_send_email and not should_send_sms:
            return

        if hr_models.TimeSheet.objects.filter(shift_ended_at__date=today, going_to_work_confirmation=True,
                                              supervisor=supervisor).exists():

            today_shift_end = hr_models.TimeSheet.objects.filter(
                shift_ended_at__date=today,
                going_to_work_confirmation=True,
                supervisor=supervisor
            ).latest('shift_ended_at').shift_ended_at

            timesheets = hr_models.TimeSheet.objects.filter(
                shift_ended_at__date=today,
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

            signed_timesheets_started = timesheets.filter(
                candidate_submitted_at__isnull=False,
                supervisor=supervisor
            ).order_by('shift_started_at').values_list(
                'shift_started_at', flat=True
            ).distinct()
            signed_timesheets_started = list(signed_timesheets_started)

            if timesheet.shift_started_at not in signed_timesheets_started:
                signed_timesheets_started.append(timesheet.shift_started_at)

            if len(signed_timesheets_started) == 0:
                return

            send_supervisor_timesheet_message(supervisor, should_send_sms, should_send_email, sms_tpl, email_tpl)

            eta = now + timedelta(hours=4)
            is_today_reminder = True
            if eta.time() > time(19, 0):
                is_today_reminder = False
                eta = timezone.make_aware(datetime.combine(date.today(), time(19, 0)))
            elif eta.time() < time(7, 0):
                eta = timezone.make_aware(datetime.combine(date.today(), time(7, 0)))

            if eta.weekday() in range(5) and not core_models.PublicHoliday.is_holiday(eta.date()):
                send_supervisor_timesheet_sign_reminder.apply_async(args=[supervisor_id, is_today_reminder], eta=eta)
    except Exception as e:
        logger.error(e)


@app.task(bind=True)
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
        supervisor_approved_at_at__isnull=True,
        supervisor=supervisor
    )

    if timesheets.exists():
        send_supervisor_timesheet_message(
            supervisor, supervisor.by_sms, supervisor.by_email, 'supervisor-timesheet-sign-reminder'
        )


@shared_task
def check_unpaid_invoices():
    master_companies = core_models.Company.objects.filter(provider_invoices__is_paid=False).distinct()

    for company in master_companies:
        unpaid_invoices = core_models.Invoice.objects.filter(provider_company=company, is_paid=False)
        date_from = unpaid_invoices.order_by('-date')[0].date - timedelta(days=32)
        cf_token = MYOBCompanyFileToken.objects.filter(company=company).latest('created')
        client = MYOBClient(cf_data=cf_token)
        initialized = client.init_api(timeout=True)

        if not initialized:
            continue

        params = {"$filter": "Status eq 'Closed' and Date gt datetime'%s'" % date_from.strftime('%Y-%m-%d')}
        invoices = client.api.Sale.Invoice.Service.get(params=params)['Items']
        invoice_numbers = [x['Number'] for x in invoices]
        closed_invoices = core_models.Invoice.objects.filter(is_paid=False, number__in=invoice_numbers)
        closed_invoices.update(is_paid=True)
