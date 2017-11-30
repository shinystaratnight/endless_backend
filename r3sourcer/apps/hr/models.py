from datetime import timedelta, date, time, datetime
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _
from filer.models import Folder
from model_utils import Choices

from r3sourcer.apps.core.decorators import workflow_function
from r3sourcer.apps.core.models import (
    UUIDModel, Contact, CompanyContact, Company, Address, Country,
    AbstractPayRuleMixin, AbstractBaseOrder, Order
)
from r3sourcer.apps.core.mixins import CategoryFolderMixin
from r3sourcer.apps.core.workflow import WorkflowProcess
from r3sourcer.apps.logger.main import endless_logger
from r3sourcer.apps.candidate.models import CandidateContact
from r3sourcer.apps.skills.models import Skill, SkillBaseRate
from r3sourcer.apps.sms_interface.models import SMSMessage
from r3sourcer.apps.pricing.models import Industry

from .utils.utils import (
    today_12_pm, today_3_30_pm, tomorrow, today_7_am, today_12_30_pm
)


NOT_FULFILLED, FULFILLED, LIKELY_FULFILLED, IRRELEVANT = range(4)


class Jobsite(
        CategoryFolderMixin,
        UUIDModel,
        WorkflowProcess):

    industry = models.ForeignKey(
        Industry,
        related_name="jobsites",
        verbose_name=_("Industry"),
        on_delete=models.PROTECT
    )

    master_company = models.ForeignKey(
        Company,
        related_name="jobsites",
        verbose_name=_("Master company"),
        on_delete=models.PROTECT
    )

    portfolio_manager = models.ForeignKey(
        CompanyContact,
        related_name="managed_jobsites",
        verbose_name=_("Portfolio Manager"),
        on_delete=models.PROTECT,
        null=True
    )

    primary_contact = models.ForeignKey(
        CompanyContact,
        related_name="jobsites",
        verbose_name=_("Primary Contact"),
        on_delete=models.PROTECT,
        null=True
    )

    is_available = models.BooleanField(
        verbose_name=_("Available"),
        default=True
    )

    notes = models.TextField(
        verbose_name=_("Notes"),
        blank=True
    )

    start_date = models.DateField(
        verbose_name=_("Start Date"),
        null=True,
        blank=True
    )

    end_date = models.DateField(
        verbose_name=_("End Date"),
        null=True,
        blank=True
    )

    files = models.ForeignKey(
        Folder,
        related_name='jobsites',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Jobsite")
        verbose_name_plural = _("Jobsites")

    def __str__(self):
        return self.get_site_name()

    def get_availability(self):
        today = date.today()
        unavailable = self.jobsite_unavailabilities.filter(
            unavailable_from__lte=today,
            unavailable_until__gte=today
        )
        if len(unavailable) > 0:
            return False
        else:
            return self.is_available

    def get_site_name(self):
        address = self.get_address()
        if address:
            return "{}, {}, {}".format(
                self.master_company, address.city, address.street_address
            )
        else:
            return str(self.master_company)

    def get_address(self):
        if self.jobsite_addresses.exists():
            return self.jobsite_addresses.first().address
        else:
            return None

    def get_duration(self):
        return self.end_date - self.start_date

    @workflow_function
    def is_address_set(self):
        return self.jobsite_addresses.all().count() > 0
    is_address_set.short_description = _("Address is required.")

    @workflow_function
    def is_supervisor_set(self):
        return self.primary_contact and self.primary_contact.contact.email
    is_supervisor_set.short_description = \
        _("Supervisor with valid email is required.")

    def save(self, *args, **kwargs):
        just_added = self._state.adding
        changed_primary_contact = False
        if not just_added:
            original = Jobsite.objects.get(id=self.id)
            changed_primary_contact = \
                original.primary_contact != self.primary_contact
        super().save(*args, **kwargs)

        if not just_added and changed_primary_contact:
            # update supervisor related future timesheets
            for vacancy in self.vacancies.all():
                for vd in vacancy.vacancy_dates.all():
                    TimeSheet.objects.filter(
                        vacancy_offer__in=vd.vacancy_offers,
                        shift_started_at__date__gte=tomorrow()
                    ).update(supervisor=self.primary_contact)

    def get_closest_company(self):
        return self.master_company


class JobsiteUnavailability(UUIDModel):

    jobsite = models.ForeignKey(
        Jobsite,
        related_name="jobsite_unavailabilities",
        verbose_name=_("Jobsite"),
        on_delete=models.PROTECT
    )

    unavailable_from = models.DateField(
        verbose_name=_("From"),
        null=True,
        blank=True
    )

    unavailable_until = models.DateField(
        verbose_name=_("Until"),
        null=True,
        blank=True
    )

    notes = models.TextField(
        verbose_name=_("Notes"),
        help_text=_("Unavailability Description"),
        blank=True
    )

    class Meta:
        verbose_name = _("Jobsite Unavailability")
        verbose_name_plural = _("Jobsite Unavailabilities")


class JobsiteAddress(UUIDModel):

    address = models.ForeignKey(
        Address,
        related_name='jobsite_addresses',
        on_delete=models.PROTECT,
        verbose_name=_("Address"),
    )

    jobsite = models.ForeignKey(
        Jobsite,
        related_name="jobsite_addresses",
        on_delete=models.PROTECT,
        verbose_name=_("Jobsite")
    )

    regular_company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="jobsite_addresses",
        verbose_name=_("Regular company")
    )

    class Meta:
        verbose_name = _("Jobsite Address")
        verbose_name_plural = _("Jobsite Addresses")


class Vacancy(AbstractBaseOrder):

    jobsite = models.ForeignKey(
        Jobsite,
        related_name="vacancies",
        on_delete=models.PROTECT,
        verbose_name=_("Jobsite")
    )

    position = models.ForeignKey(
        Skill,
        related_name="vacancies",
        on_delete=models.PROTECT,
        verbose_name=_("Category")
    )

    published = models.BooleanField(
        default=False,
        verbose_name=_("Published")
    )

    publish_on = models.DateField(
        verbose_name=_("To be published on"),
        null=True,
        blank=True
    )

    expires_on = models.DateField(
        verbose_name=_("Expires on"),
        null=True,
        blank=True
    )

    work_start_date = models.DateField(
        verbose_name=_("Work Start Date"),
        default=date.today
    )

    workers = models.PositiveSmallIntegerField(
        verbose_name=_("Workers"),
        default=1,
        validators=[MinValueValidator(1)]
    )

    default_shift_starting_time = models.TimeField(
        verbose_name=_('Default Shift Starting Time'),
        default=time(hour=7)
    )

    notes = models.TextField(
        verbose_name=_("Notes"),
        help_text=_("Vacancy Description"),
        blank=True
    )

    TRANSPORTATION_CHOICES = Choices(
        (1, 'own', _("Own Car")),
        (2, 'public', _("Public Transportation")),
    )

    transportation_to_work = models.PositiveSmallIntegerField(
        choices=TRANSPORTATION_CHOICES,
        verbose_name=_("Transportation to Work"),
        null=True,
        blank=True
    )

    hourly_rate_default = models.ForeignKey(
        SkillBaseRate,
        related_name="vacancies",
        on_delete=models.SET_NULL,
        verbose_name=_("Hourly rate default"),
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _("Vacancy")
        verbose_name_plural = _("Vacancies")
        unique_together = ('work_start_date', 'position', 'jobsite')

    def __str__(self):
        return self.get_title()

    def get_title(self):
        return _('{} {}s at {}').format(
            str(self.workers),
            str(self.position),
            str(self.jobsite),
        )
    get_title.short_description = _('Title')

    def get_vacancy_offers(self):
        return VacancyOffer.objects.filter(shift__date__vacancy=self)

    def get_total_bookings_count(self):
        return self.get_vacancy_offers().distinct('candidate_contact').count()
    get_total_bookings_count.short_description = _('Bookings')

    def is_fulfilled(self):
        # FIXME: change to new workflow
        # if self.get_state() in [OrderState.STATE_CHOICES.cancelled,
        #                               OrderState.STATE_CHOICES.completed]:
        #     return IRRELEVANT

        result = NOT_FULFILLED
        now = timezone.now()
        today = now.date()
        next_date = self.vacancy_dates.filter(
            shift_date__gt=today, cancelled=False
        ).order_by('shift_date').first()

        if next_date is not None:
            result = next_date.is_fulfilled()
            if result == NOT_FULFILLED and next_date.vacancy_offers.exists():
                unaccepted_vos = next_date.vacancy_offers.filter(
                    status=VacancyOffer.STATUS_CHOICES.undefined
                )

                for unaccepted_vo in unaccepted_vos.all():
                    todays_timesheets = unaccepted_vo.time_sheets.filter(
                        going_to_work_confirmation=True,
                        shift_started_at__lte=now,
                        shift_ended_at__gte=now + timedelta(hours=1),
                    )

                    if not todays_timesheets.exists():
                        return NOT_FULFILLED
                result = LIKELY_FULFILLED
        else:
            result = IRRELEVANT
        return result
    is_fulfilled.short_description = _('Fulfilled')

    def is_fulfilled_today(self):
        # FIXME: change to new workflow
        # if self.order.get_state() in [OrderState.STATE_CHOICES.cancelled,
        #                               OrderState.STATE_CHOICES.completed]:
        #     return IRRELEVANT

        result = NOT_FULFILLED
        today = timezone.now().date()
        vd_today = self.vacancy_dates.filter(shift_date=today, cancelled=False).first()
        if vd_today:
            result = vd_today.is_fulfilled()
        else:
            result = IRRELEVANT
        return result

    def can_fillin(self):
        not_filled_future_vd = False
        today = timezone.now().date()
        future_vds = self.vacancy_dates.filter(shift_date__gte=today)
        for vd in future_vds:
            if vd.is_fulfilled() == NOT_FULFILLED:
                not_filled_future_vd = True
                break

        # FIXME: change to new workflow
        # return self.order.get_state() not in [OrderState.STATE_CHOICES.cancelled,
        #                                       OrderState.STATE_CHOICES.completed,
        #                                       OrderState.STATE_CHOICES.new] and \
        return self.is_fulfilled() in [NOT_FULFILLED, LIKELY_FULFILLED] or not_filled_future_vd


class VacancyDate(UUIDModel):

    vacancy = models.ForeignKey(
        Vacancy,
        related_name="vacancy_dates",
        on_delete=models.CASCADE,
        verbose_name=_("Vacancy")
    )

    shift_date = models.DateField(
        verbose_name=_("Shift date")
    )

    workers = models.PositiveSmallIntegerField(
        verbose_name=_("Workers"),
        default=1,
        validators=[MinValueValidator(1)]
    )

    hourly_rate = models.ForeignKey(
        SkillBaseRate,
        related_name="vacancy_dates",
        on_delete=models.SET_NULL,
        verbose_name=_("Hourly rate"),
        null=True,
        blank=True
    )

    cancelled = models.BooleanField(
        default=False
    )

    class Meta:
        verbose_name = _("Vacancy Date")
        verbose_name_plural = _("Vacancy dates")

    def __str__(self):
        return '{}, {}: {}'.format(
            date_format(
                self.shift_date,
                settings.DATE_FORMAT
            ),
            _("workers"), self.workers
        )

    @property
    def vacancy_offers(self):
        return VacancyOffer.objects.filter(shift__date=self)

    def is_fulfilled(self):
        result = NOT_FULFILLED
        vos = self.vacancy_offers
        accepted_vos = vos.filter(status=VacancyOffer.STATUS_CHOICES.accepted)

        if vos.exists() and self.workers <= accepted_vos.count():
            result = FULFILLED
        return result
    is_fulfilled.short_description = _('Fulfilled')


class Shift(UUIDModel):
    time = models.TimeField(verbose_name=_("Time"))

    date = models.ForeignKey(
        VacancyDate,
        related_name="vacancy_dates",
        on_delete=models.CASCADE,
        verbose_name=_("Date")
    )

    class Meta:
        verbose_name = _("Shift")
        verbose_name_plural = _("Shifts")

    def __str__(self):
        return date_format(
            datetime.combine(self.date.shift_date, self.time),
            settings.DATETIME_FORMAT
        )

    @property
    def vacancy(self):
        return self.date.vacancy


class VacancyOffer(UUIDModel):

    sent_sms_field = 'offer_sent_by_sms'
    receive_sms_field = 'reply_received_by_sms'

    shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name='vacancy_offers',
        verbose_name=_("Shift")
    )

    candidate_contact = models.ForeignKey(
        CandidateContact,
        verbose_name=_("Candidate contact"),
        on_delete=models.PROTECT,
        related_name='vacancy_offers'
    )

    offer_sent_by_sms = models.ForeignKey(
        SMSMessage,
        null=True,
        blank=True,
        verbose_name=_("Offer sent by sms"),
        on_delete=models.PROTECT,
        related_name='vacancy_offers'
    )

    reply_received_by_sms = models.ForeignKey(
        SMSMessage,
        verbose_name=_("Reply received by sms"),
        related_name='reply_vacancy_offers',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    STATUS_CHOICES = Choices(
        (0, 'undefined', _("Undefined")),
        (1, 'accepted', _("Accepted")),
        (2, 'cancelled', _("Cancelled")),
    )

    status = models.PositiveSmallIntegerField(
        verbose_name=_("Status"),
        choices=STATUS_CHOICES,
        default=STATUS_CHOICES.undefined
    )

    scheduled_sms_datetime = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Scheduled date")
    )

    class Meta:
        verbose_name = _("Vacancy offer")
        verbose_name_plural = _("Vacancy offers")

    def __str__(self):
        return '{}'.format(date_format(
            timezone.localtime(self.created_at), settings.DATETIME_FORMAT
        ))

    @property
    def vacancy(self):
        return self.shift.vacancy

    @property
    def start_time(self):
        return timezone.make_aware(
            datetime.combine(self.shift.date.shift_date, self.shift.time)
        )

    def is_accepted(self):
        return self.status == VacancyOffer.STATUS_CHOICES.accepted

    def is_recurring(self):
        return self.vacancy.get_vacancy_offers().filter(
            candidate_contact=self.candidate_contact,
            shift__date__shift_date__lt=self.shift.date.shift_date,
            status=VacancyOffer.STATUS_CHOICES.accepted
        ).exists()

    def is_first(self):
        return not self.vacancy.get_vacancy_offers().filter(
            candidate_contact=self.candidate_contact,
            shift__date__shift_date__lt=self.shift.date.shift_date
        ).exists()

    def get_future_offers(self):
        return self.vacancy.get_vacancy_offers().filter(
            candidate_contact=self.candidate_contact,
            shift__date__shift_date__gt=self.shift.date.shift_date
        )


class TimeSheet(
        UUIDModel,
        WorkflowProcess):

    sent_sms_field = 'going_to_work_sent_sms'
    receive_sms_field = 'going_to_work_reply_sms'

    vacancy_offer = models.ForeignKey(
        VacancyOffer,
        on_delete=models.CASCADE,
        related_name="time_sheets",
        verbose_name=_("Vacancy Offer")
    )

    going_to_work_sent_sms = models.ForeignKey(
        SMSMessage,
        verbose_name=_('Going to Work Sent SMS'),
        related_name='time_sheets_going_to_work',
        blank=True,
        null=True,
        on_delete=models.PROTECT
    )

    going_to_work_reply_sms = models.ForeignKey(
        SMSMessage,
        verbose_name=_('Going to Work Reply SMS'),
        related_name='time_sheets_going_to_work_reply',
        blank=True,
        null=True,
        on_delete=models.PROTECT
    )

    going_to_work_confirmation = models.NullBooleanField(
        verbose_name=_("Going to Work")
    )

    shift_started_at = models.DateTimeField(
        verbose_name=_("Shift Started at"),
        null=True,
        blank=True,
        default=today_7_am
    )

    break_started_at = models.DateTimeField(
        verbose_name=_("Break Started at"),
        null=True,
        blank=True,
        default=today_12_pm
    )

    break_ended_at = models.DateTimeField(
        verbose_name=_("Break Ended at"),
        null=True,
        blank=True,
        default=today_12_30_pm
    )

    shift_ended_at = models.DateTimeField(
        verbose_name=_("Shift Ended at"),
        null=True,
        blank=True,
        default=today_3_30_pm
    )

    supervisor = models.ForeignKey(
        CompanyContact,
        related_name="supervised_time_sheets",
        on_delete=models.PROTECT,
        verbose_name=_("Supervisor"),
        blank=True,
        null=True
    )

    def supervisor_signature_path(self, filename):
        """ Supervisor signature upload handler """

        ext = filename.split('.')[-1]
        pattern = 'timesheets/signature/{ts_id}.{ext}'
        return pattern.format(
            ts_id=self.id,
            ext=ext
        )

    supervisor_signature = models.ImageField(
        _("Supervisor signature"),
        upload_to=supervisor_signature_path,
        blank=True,
        null=True,
    )

    candidate_submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Candidate Submitted at")
    )

    supervisor_approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Supervisor Approved at")
    )

    supervisor_approved_scheme = models.CharField(
        verbose_name=_("Supervisor Approved scheme"),
        max_length=16,
        default='',
        choices=Company.TIMESHEET_APPROVAL_SCHEME,
        editable=False
    )

    candidate_rate = models.ForeignKey(
        SkillBaseRate,
        related_name="timesheets",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Candidate Rate Override")
    )

    rate_overrides_approved_by = models.ForeignKey(
        CompanyContact,
        related_name='timesheet_rate_override_approvals',
        on_delete=models.PROTECT,
        verbose_name=_("Candidate and Client Rate Overrides Approved by"),
        null=True,
        blank=True
    )

    rate_overrides_approved_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Candidate and Client Rate Overrides Approved at")
    )

    __original_supervisor_id = None
    __original_going_to_work_confirmation = None
    __original_candidate_submitted_at = None
    sms_triggered_action = False

    class Meta:
        verbose_name = _("Timesheet Entry")
        verbose_name_plural = _("Timesheet Entries")
        unique_together = ("vacancy_offer", "shift_started_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__original_supervisor_id = self.supervisor_id
        self.__original_going_to_work_confirmation = \
            self.going_to_work_confirmation
        self.__original_candidate_submitted_at = self.candidate_submitted_at

    def __str__(self):
        return '{} {} {}'.format(
            date_format(timezone.localtime(self.shift_started_at),
                        settings.DATETIME_FORMAT)
            if self.shift_started_at else '',
            date_format(timezone.localtime(self.candidate_submitted_at),
                        settings.DATETIME_FORMAT)
            if self.candidate_submitted_at else '',
            date_format(timezone.localtime(self.supervisor_approved_at),
                        settings.DATETIME_FORMAT)
            if self.supervisor_approved_at else ''
        )

    def get_vacancy_offer(self):
        return self.vacancy_offer

    @classmethod
    def get_or_create_for_vacancy_offer_accepted(cls, vacancy_offer):
        data = {
            'vacancy_offer': vacancy_offer,
            'shift_started_at': vacancy_offer.start_time,
            'break_started_at': vacancy_offer.start_time + timedelta(hours=5),
            'break_ended_at':
                vacancy_offer.start_time + timedelta(hours=5, minutes=30),
            'shift_ended_at':
                vacancy_offer.start_time + timedelta(hours=8, minutes=30),
            'supervisor': vacancy_offer.vacancy.jobsite.primary_contact,
            'candidate_rate': vacancy_offer.shift.date.hourly_rate
        }

        try:
            time_sheet, created = cls.objects.get_or_create(**data)
        except IntegrityError:
            time_sheet, created = cls.objects.update_or_create(
                vacancy_offer=vacancy_offer,
                shift_started_at=vacancy_offer.start_time,
                defaults=data
            )

        now = timezone.now()
        if now <= vacancy_offer.start_time + timedelta(hours=2):
            pass  # pragma: no cover
            # TODO: send sms?
            # from pepro.crm_hr.tasks import send_placement_acceptance_sms
            # send_placement_acceptance_sms.apply_async(
            #     args=[vacancy_offer.id], countdown=10
            # )

        return time_sheet

    def get_closest_company(self):
        return self.get_vacancy_offer().vacancy.get_closest_company()

    def save(self, *args, **kwargs):
        just_added = self._state.adding
        super().save(*args, **kwargs)

        if just_added:
            self.create_state(10)


class TimeSheetIssue(
        UUIDModel,
        WorkflowProcess):

    time_sheet = models.ForeignKey(
        TimeSheet,
        on_delete=models.PROTECT,
        related_name="timesheet_issues",
        verbose_name=_("TimeSheet")
    )

    subject = models.CharField(
        max_length=255,
        verbose_name=_("Subject")
    )

    description = models.TextField(
        verbose_name=_("Description")
    )

    supervisor = models.ForeignKey(
        CompanyContact,
        related_name="supervised_timesheet_issues",
        on_delete=models.PROTECT,
        verbose_name=_("Supervisor")
    )

    supervisor_approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Supervisor Approved at")
    )

    account_representative = models.ForeignKey(
        CompanyContact,
        related_name="timesheet_issues",
        verbose_name=_("Account Contact Responsible"),
        on_delete=models.PROTECT,
        null=True
    )

    class Meta:
        verbose_name = _("Timesheet Issue")
        verbose_name_plural = _("Timesheet Issues")

    def __str__(self):
        return '{}: {}'.format(str(self.time_sheet), str(self.subject))

    def get_closest_company(self):
        return self.time_sheet.get_closest_company()


class BlackList(UUIDModel):

    company = models.ForeignKey(
        Company,
        related_name="blacklists",
        on_delete=models.PROTECT,
        verbose_name=_("Company")
    )

    candidate_contact = models.ForeignKey(
        CandidateContact,
        on_delete=models.PROTECT,
        related_name="blacklists",
        verbose_name=_("Candidate Contact")
    )

    timesheet = models.ForeignKey(
        TimeSheet,
        verbose_name=_('Timesheet'),
        related_name='blacklists',
        blank=True,
        null=True,
        on_delete=models.PROTECT
    )

    jobsite = models.ForeignKey(
        Jobsite,
        verbose_name=_('Jobsite'),
        related_name='blacklists',
        blank=True,
        null=True,
        on_delete=models.PROTECT
    )

    company_contact = models.ForeignKey(
        CompanyContact,
        verbose_name=_('Company Contact'),
        related_name='blacklists',
        blank=True,
        null=True,
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = _("Black list")
        verbose_name_plural = _("Black lists")
        unique_together = ('company', 'company_contact', 'candidate_contact', 'timesheet', 'jobsite')

    def __str__(self):
        return "{}: {}".format(str(self.company), str(self.candidate_contact))

    def clean(self):
        """
        Checks that we do not create multiple BlackList items
        with same fields values.
        """
        if self.timesheet and not self.jobsite:
            self.jobsite = self.timesheet.vacancy_offer.vacancy.jobsite
        if self.timesheet and not self.company_contact:
            self.company_contact = self.timesheet.supervisor
        if BlackList.objects.filter(
            company=self.company,
            company_contact=self.company_contact,
            candidate_contact=self.candidate_contact,
            timesheet=self.timesheet,
            jobsite=self.jobsite,
        ).exists():
            raise ValidationError(_('Another BlackList item with such parameters already exists'))
        super().clean()


class FavouriteList(UUIDModel):

    company_contact = models.ForeignKey(
        CompanyContact,
        related_name='favouritelist',
        verbose_name=_('Favourite list owner'),
        on_delete=models.CASCADE
    )

    candidate_contact = models.ForeignKey(
        CandidateContact,
        related_name="favouritelists",
        verbose_name=_("Candidate Contact"),
        on_delete=models.CASCADE,
    )

    company = models.ForeignKey(
        Company,
        related_name="favouritelists",
        verbose_name=_("Company"),
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )

    jobsite = models.ForeignKey(
        Jobsite,
        verbose_name=_('Jobsite'),
        related_name='favouritelists',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    vacancy = models.ForeignKey(
        Vacancy,
        verbose_name=_('Vacancy'),
        related_name='favouritelists',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _("Favourite list")
        verbose_name_plural = _("Favourite lists")
        unique_together = ('company_contact', 'candidate_contact', 'company', 'jobsite', 'vacancy')

    def __str__(self):
        return "{}: {}".format(str(self.company_contact), str(self.candidate_contact))

    def clean(self):
        """
        Checks that we do not create multiple FavouriteList items
        with same fields values.
        """
        if not hasattr(self, 'candidate_contact'):
            raise ValidationError({
                'candidate_contact': _('Please select Candidate Contact')
            })

        if self.vacancy:
            self.jobsite = self.vacancy.jobsite
        if self.jobsite:
            self.company = self.jobsite.master_company
        if FavouriteList.objects.filter(
            company_contact=self.company_contact,
            candidate_contact=self.candidate_contact,
            company=self.company,
            jobsite=self.jobsite,
            vacancy=self.vacancy,
        ).exists() and not (self.company and self.jobsite and self.vacancy):
            raise ValidationError(_('Another FavoritList item with such parameters already exists'))
        super().clean()


class CarrierList(UUIDModel):

    candidate_contact = models.ForeignKey(
        CandidateContact,
        on_delete=models.PROTECT,
        related_name='carrier_lists',
        verbose_name=_('Candidate Contact'),
        blank=True,
        null=True
    )

    target_date = models.DateField(
        verbose_name=_('Target Date'),
        default=tomorrow
    )

    confirmed_available = models.BooleanField(
        default=False,
        verbose_name=_('Confirmed Available')
    )

    sent_message = models.ForeignKey(
        SMSMessage,
        verbose_name=_('Sent SMS Message'),
        related_name='sent_carrier_lists',
        blank=True,
        null=True
    )

    reply_message = models.ForeignKey(
        SMSMessage,
        verbose_name=_('Reply SMS Message'),
        related_name='reply_carrier_lists',
        blank=True,
        null=True
    )

    vacancy_offer = models.ForeignKey(
        VacancyOffer,
        verbose_name=_('Vacancy Offer'),
        related_name='carrier_lists',
        blank=True,
        null=True
    )

    referral_vacancy_offer = models.ForeignKey(
        VacancyOffer,
        verbose_name=_('Referral Vacancy Offer'),
        related_name='referral_carrier_lists',
        blank=True,
        null=True
    )

    sms_sending_scheduled_at = models.DateTimeField(
        verbose_name=_("SMS sending scheduled at"),
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _("Carrier List")
        verbose_name_plural = _("Carrier Lists")
        unique_together = ('candidate_contact', 'target_date')

    def __str__(self):
        return '{}: {}'.format(
            str(self.candidate_contact),
            date_format(self.target_date, settings.DATE_FORMAT)
        )

    def confirm(self):
        self.confirmed_available = True
        self.save(update_fields=['confirmed_available'])

    def deny(self):
        self.confirmed_available = False
        self.save(update_fields=['confirmed_available'])


class CandidateEvaluation(UUIDModel):

    candidate_contact = models.ForeignKey(
        CandidateContact,
        on_delete=models.PROTECT,
        related_name="candidate_evaluations",
        verbose_name=_("Candidate Contact")
    )

    supervisor = models.ForeignKey(
        CompanyContact,
        related_name="supervised_candidate_evaluations",
        on_delete=models.PROTECT,
        verbose_name=_("Supervisor"),
        blank=True,
        null=True
    )

    evaluated_at = models.DateTimeField(
        verbose_name=_("Evaluated at"),
        auto_now_add=True,
        blank=True,
        null=True
    )

    reference_timesheet = models.ForeignKey(
        TimeSheet,
        on_delete=models.CASCADE,
        related_name="candidate_evaluations",
        verbose_name=_("Reference TimeSheet"),
        blank=True,
        null=True
    )

    LEVEL_OF_COMMUNICATION_CHOICES = Choices(
        (0, 'unrated', _("Not Rated")),
        (1, 'impossible', _("Impossible")),
        (2, 'hard', _("Hard")),
        (3, 'decent', _("Decent")),
        (4, 'good', _("Good")),
        (5, 'excellent', _("Excellent")),
    )

    level_of_communication = models.PositiveSmallIntegerField(
        verbose_name=_("Level of Communication"),
        choices=LEVEL_OF_COMMUNICATION_CHOICES,
        default=LEVEL_OF_COMMUNICATION_CHOICES.unrated
    )

    was_on_time = models.NullBooleanField(
        verbose_name=_("Was on time?")
    )
    was_motivated = models.NullBooleanField(
        verbose_name=_("Was motivated?")
    )
    had_ppe_and_tickets = models.NullBooleanField(
        verbose_name=_("Had PPE and tickets?")
    )
    met_expectations = models.NullBooleanField(
        verbose_name=_("Met Your expectations?")
    )
    representation = models.NullBooleanField(
        verbose_name=_("Was clean, well presented?")
    )

    class Meta:
        verbose_name = _("Candidate Evaluation")
        verbose_name_plural = _("Candidate Evaluations")

    def _calc_rating(self):
        rating = 0
        if self.was_on_time:
            rating += 1
        if self.was_motivated:
            rating += 1
        if self.had_ppe_and_tickets:
            rating += 1
        if self.met_expectations:
            rating += 1
        if self.representation:
            rating += 1
        return rating

    def get_rating(self):
        rating = self._calc_rating()
        if rating > 0:
            rating = (rating + self.level_of_communication) / 2
        return rating
    get_rating.short_description = _('Rating')

    def single_evaluation_average(self):
        return (self._calc_rating() + self.level_of_communication) / 2
    single_evaluation_average.short_description = _("Jobsite Feedback")


class ContactJobsiteDistanceCache(UUIDModel):
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='distance_caches',
        verbose_name=_("Contact")
    )

    jobsite = models.ForeignKey(
        Jobsite,
        on_delete=models.CASCADE,
        related_name='distance_caches',
        verbose_name=_("Jobsite")
    )

    distance = models.CharField(max_length=10)

    time = models.CharField(max_length=10, null=True, blank=True)

    updated_at = models.DateTimeField(
        verbose_name=_("Updated at"),
        auto_now=True,
        editable=False,
        null=True
    )

    class Meta:
        unique_together = ("contact", "jobsite")


class Payslip(UUIDModel):

    payment_date = models.DateField(
        verbose_name=_("Payment Date"),
        null=True,
        blank=True
    )

    annual_salary = models.DecimalField(
        verbose_name=_("Annual salary"),
        max_digits=8,
        decimal_places=2,
        default=0
    )

    hourly_rate = models.ForeignKey(
        SkillBaseRate,
        related_name="payslips",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("Hourly rate"),
    )

    from_date = models.DateField(
        verbose_name=_("From Date")
    )

    to_date = models.DateField(
        verbose_name=_("To Date")
    )

    company = models.ForeignKey(
        Company,
        verbose_name=_("Company"),
        related_name="payslips",
        null=True,
        blank=True
    )

    candidate = models.ForeignKey(
        CandidateContact,
        verbose_name=_("Candidate contact"),
        related_name="payslips"
    )

    cheque_number = models.TextField(
        verbose_name=_("Cheque number")
    )

    class Meta:
        verbose_name = _("Payslip")
        verbose_name_plural = _("Payslips")

    def save(self, *args, **kwargs):
        just_added = self._state.adding
        if just_added:
            rule = None
            if self.company.payslip_rules.exists():
                rule = self.company.payslip_rules.first()
            else:
                master_company = self.company.get_master_company()[0]
                if master_company.payslip_rules.exists():
                    rule = master_company.payslip_rules.first()

            if rule:
                self.cheque_number = str(rule.starting_number)
                rule.starting_number += 1
                rule.save()

        super(Payslip, self).save(*args, **kwargs)

    def get_gross_pay(self):
        sum_pay = Decimal()
        for line in self.payslip_lines.filter(type=0).all():
            sum_pay += line.amount

        return sum_pay

    def get_wage_pay(self):
        pay = self.get_gross_pay()
        pay += self.get_payg_pay()

        return pay

    def get_payg_pay(self):
        sum_pay = Decimal()
        for line in self.payslip_lines.filter(type=1).all():
            sum_pay += line.amount

        return sum_pay

    def get_superannuation_pay(self):
        sum_pay = Decimal()
        for line in self.payslip_lines.filter(type=2).all():
            sum_pay += line.amount

        return sum_pay


class PayslipRule(AbstractPayRuleMixin, UUIDModel):

    company = models.ForeignKey(
        Company,
        related_name="payslip_rules",
        verbose_name=_("Company"),
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = _("Payslip Rule")
        verbose_name_plural = _("Payslip Rules")


class PayslipLine(UUIDModel):

    description = models.CharField(
        max_length=255,
        verbose_name=_("Description")
    )

    hours = models.DecimalField(
        verbose_name=_("Hours"),
        max_digits=8,
        decimal_places=2,
        default=0
    )

    calc_rate = models.DecimalField(
        verbose_name=_("Calc. Rate"),
        max_digits=8,
        decimal_places=2,
        default=0
    )

    amount = models.DecimalField(
        verbose_name=_("Amount"),
        max_digits=8,
        decimal_places=2
    )

    ytd = models.DecimalField(
        verbose_name=_("YTD"),
        max_digits=8,
        decimal_places=2,
        default=0
    )

    TYPE_CHOICES = Choices(
        (0, 'wages', _('Wages')),
        (1, 'tax', _('Tax')),
        (2, 'superannuation', _('Superannuation Expenses')),
    )

    type = models.PositiveSmallIntegerField(
        choices=TYPE_CHOICES,
        verbose_name=_('Type'),
    )

    payslip = models.ForeignKey(
        Payslip,
        related_name="payslip_lines",
        verbose_name=_("Payslip"),
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = _("Payslip Line")
        verbose_name_plural = _("Payslip Lines")

    def get_type(self):
        return self.TYPE_CHOICES[self.type]


class PersonalIncomeTax(UUIDModel):

    country = models.ForeignKey(
        Country,
        to_field='code2',
        default='AU'
    )

    name = models.CharField(
        max_length=64,
        verbose_name=_("Name"),
    )

    PERIOD_CHOICES = Choices(
        ('weekly', _('Weekly')),
        ('fortnightly', _('Fortnightly')),
        ('monthly', _('Monthly')),
        ('daily', _('Daily'))
    )

    period = models.CharField(
        max_length=11,
        verbose_name=_("Period"),
        choices=PERIOD_CHOICES,
        default=PERIOD_CHOICES.weekly
    )

    rule = models.CharField(
        max_length=255,
        verbose_name=_("Rule")
    )

    start_date = models.DateField(
        verbose_name=_("Start Date")
    )

    end_date = models.DateField(
        verbose_name=_("End Date"),
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _("Personal Income Tax")
        verbose_name_plural = _("Personal Income Taxes")


class SocialInsurance(UUIDModel):

    country = models.ForeignKey(
        Country,
        to_field='code2',
        default='AU'
    )

    name = models.CharField(
        max_length=64,
        verbose_name=_("Name"),
        default=_("Superannuation")
    )

    threshold = models.DecimalField(
        decimal_places=2,
        max_digits=16,
        verbose_name=_("Threshold"),
        default=0.00
    )

    rate = models.DecimalField(
        decimal_places=2,
        max_digits=16,
        verbose_name=_("Rate"),
        default=0.00
    )

    start_date = models.DateField(
        verbose_name=_("Start Date")
    )

    end_date = models.DateField(
        verbose_name=_("End Date"),
        blank=True,
        null=True
    )

    age_threshold = models.IntegerField(
        verbose_name=_("Age threshold"),
        default=18,
        null=True
    )

    class Meta:
        verbose_name = _("Social Insurance")
        verbose_name_plural = _("Social Insurances")


class CandidateScore(UUIDModel):

    candidate_contact = models.OneToOneField(
        CandidateContact,
        on_delete=models.CASCADE,
        related_name="candidate_scores",
        verbose_name=_("Candidate Scores"),
        null=True,
        blank=True,
    )

    client_feedback = models.DecimalField(
        decimal_places=2,
        max_digits=3,
        verbose_name=_("Client Feedback"),
        null=True
    )

    reliability = models.DecimalField(
        decimal_places=2,
        max_digits=3,
        verbose_name=_("Reliability"),
        null=True
    )

    loyalty = models.DecimalField(
        decimal_places=2,
        max_digits=3,
        verbose_name=_("Loyalty"),
        null=True
    )

    recruitment_score = models.DecimalField(
        decimal_places=2,
        max_digits=3,
        verbose_name=_("Recruitment Score"),
        null=True
    )

    class Meta:
        verbose_name = _("Candidate Score")
        verbose_name_plural = _("Candidates' Scores")

    def recalc_client_feedback(self):
        """
        Calculate client feedback score
        :return: self
        """
        total = 0
        counter = 0
        for evaluation in self.candidate_contact.candidate_evaluations.all():
            if evaluation.single_evaluation_average() > 0:
                total += evaluation.single_evaluation_average()
                counter += 1
        self.client_feedback = total / counter if counter > 0 else None

    def recalc_reliability(self, save=True):
        """
        Calculate reliability score
        :return: self
        """
        vos = VacancyOffer.objects.filter(
            candidate_contact=self.candidate_contact
        )
        accepted_vos = vos.filter(
            status=VacancyOffer.STATUS_CHOICES.accepted
        ).count()
        cancelled_vos = endless_logger.get_history_object_ids(
            VacancyOffer, 'status', '2', ids=vos.values_list('id', flat=True)
        )
        absent_vos = len(endless_logger.get_history_object_ids(
            VacancyOffer, 'status', '1', ids=cancelled_vos
        ))

        total_vos = accepted_vos + absent_vos

        reliability = (
            5 * (accepted_vos / total_vos) if total_vos > 4 else 0
        )
        if save:
            self.reliability = reliability if reliability > 0 else None

        return reliability

    def recalc_loyalty(self):
        """
        Calculate loyalty score
        :return: self
        """
        loyalty = 0
        count = 1
        vos = VacancyOffer.objects.filter(
            candidate_contact=self.candidate_contact
        )
        accepted_vos = vos.filter(
            status=VacancyOffer.STATUS_CHOICES.accepted
        )

        # Calculate shift acceptance
        loyalty = self.recalc_reliability(False)

        # Calculate time bonus
        time_shift = timedelta(hours=1, minutes=30)
        time_bonus = len(endless_logger.get_history_object_ids(
            VacancyOffer, 'status', '1', ids=vos.values_list('id', flat=True)
        ))
        time_bonus = accepted_vos.filter(
            offer_sent_by_sms__sent_at__gte=(
                models.F('shift__date__shift_date') - time_shift
            )
        ).count()
        if time_bonus:
            loyalty += time_bonus*5
            count += time_bonus

        # Calculate distance bonus
        distances = ContactJobsiteDistanceCache.objects.filter(
            contact=self.candidate_contact.contact,
            jobsite__in=vos.values_list(
                'shift__date__vacancy__jobsite', flat=True
            ),
        )
        if (self.candidate_contact.transportation_to_work ==
                CandidateContact.TRANSPORTATION_CHOICES.own):
            distance_bonus = distances.filter(distance__gt=50000).count()
        else:
            distance_bonus = distances.filter(time__gt=3600).count()

        if distance_bonus:
            loyalty += distance_bonus*5
            count += distance_bonus

        # Calculate main loyalty value
        if count:
            self.loyalty = loyalty/count
        else:
            self.loyalty = None

    def recalc_recruitment_score(self):
        states = self.candidate_contact.get_active_states()

        score_sum = sum([s.score for s in states])

        if len(states) > 0:
            self.recruitment_score = score_sum / len(states)

    def recalc_scores(self):
        self.recalc_client_feedback()
        self.recalc_reliability()
        self.recalc_loyalty()
        self.recalc_recruitment_score()
        self.save()

    def get_average_score(self):
        total_score = 0
        scores_count = 0
        if self.client_feedback is not None:
            total_score += self.client_feedback
            scores_count += 1
        if self.reliability is not None:
            total_score += self.reliability
            scores_count += 1
        if self.loyalty is not None:
            total_score += self.loyalty
            scores_count += 1
        if self.recruitment_score is not None:
            total_score += self.recruitment_score
            scores_count += 1
        return total_score / scores_count if scores_count else None
