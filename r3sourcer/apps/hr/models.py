from datetime import timedelta, date, time, datetime
from decimal import Decimal

from crum import get_current_request
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError, transaction
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _
from filer.models import Folder
from model_utils import Choices

from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.decorators import workflow_function
from r3sourcer.apps.core.mixins import CategoryFolderMixin
from r3sourcer.apps.core.utils.user import get_default_user
from r3sourcer.apps.core.workflow import WorkflowProcess
from r3sourcer.apps.logger.main import endless_logger
from r3sourcer.apps.candidate.models import CandidateContact
from r3sourcer.apps.skills.models import Skill, SkillBaseRate
from r3sourcer.apps.sms_interface.models import SMSMessage
from r3sourcer.apps.pricing.models import Industry
from r3sourcer.apps.hr.utils import utils as hr_utils


NOT_FULFILLED, FULFILLED, LIKELY_FULFILLED, IRRELEVANT = range(4)


class Jobsite(
    CategoryFolderMixin,
    core_models.UUIDModel,
    WorkflowProcess
):

    industry = models.ForeignKey(
        Industry,
        related_name="jobsites",
        verbose_name=_("Industry"),
        on_delete=models.PROTECT
    )

    short_name = models.CharField(
        max_length=63,
        help_text=_('Used for jobsite naming'),
        verbose_name=_("Site short name"),
        blank=True,
        null=True
    )

    master_company = models.ForeignKey(
        core_models.Company,
        related_name="jobsites",
        verbose_name=_("Master company"),
        on_delete=models.PROTECT
    )

    regular_company = models.ForeignKey(
        core_models.Company,
        on_delete=models.PROTECT,
        related_name="jobsites_regular",
        verbose_name=_("Client"),
    )

    address = models.ForeignKey(
        core_models.Address,
        on_delete=models.PROTECT,
        related_name="jobsites",
        verbose_name=_("Address"),
        blank=True,
        null=True
    )

    portfolio_manager = models.ForeignKey(
        core_models.CompanyContact,
        related_name="managed_jobsites",
        verbose_name=_("Portfolio Manager"),
        on_delete=models.PROTECT,
        null=True
    )

    primary_contact = models.ForeignKey(
        core_models.CompanyContact,
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
        if self.short_name:
            return self.short_name

        job_address = self.get_address()
        if job_address:
            return "{}, {}, {}".format(
                self.regular_company, job_address.street_address, job_address.city
            )

        return str(self.master_company)

    def get_address(self):
        return self.address

    def get_duration(self):
        return self.end_date - self.start_date

    @workflow_function
    def is_address_set(self):
        return self.address is not None
    is_address_set.short_description = _("Address is required.")

    @workflow_function
    def is_supervisor_set(self):
        return self.primary_contact and self.primary_contact.contact.email
    is_supervisor_set.short_description = _("Supervisor with valid email is required.")

    def save(self, *args, **kwargs):
        just_added = self._state.adding
        changed_primary_contact = False
        if not just_added:
            original = Jobsite.objects.get(id=self.id)
            changed_primary_contact = \
                original.primary_contact != self.primary_contact

        super().save(*args, **kwargs)

        if just_added:
            if self.is_allowed(10):
                self.create_state(10)
        elif changed_primary_contact:
            # update supervisor related future timesheets
            for job in self.jobs.all():
                for sd in job.shift_dates.all():
                    TimeSheet.objects.filter(
                        job_offer__in=sd.job_offers,
                        shift_started_at__date__gte=hr_utils.tomorrow()
                    ).update(supervisor=self.primary_contact)

    def get_closest_company(self):
        return self.master_company


class JobsiteUnavailability(core_models.UUIDModel):

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


class Job(core_models.AbstractBaseOrder):

    jobsite = models.ForeignKey(
        Jobsite,
        related_name="jobs",
        on_delete=models.PROTECT,
        verbose_name=_("Jobsite")
    )

    position = models.ForeignKey(
        Skill,
        related_name="jobs",
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
        help_text=_("Job Description/Instructions for candidate"),
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

    hourly_rate_default = models.DecimalField(
        decimal_places=2,
        max_digits=16,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _("Job")
        verbose_name_plural = _("Jobs")

    def __str__(self):
        return self.get_title()

    def get_title(self):
        return _('{} {}s at {}').format(
            str(self.workers),
            str(self.position),
            str(self.jobsite),
        )
    get_title.short_description = _('Title')

    def get_job_offers(self):
        return JobOffer.objects.filter(shift__date__job=self)

    def get_total_bookings_count(self):
        return self.get_job_offers().distinct('candidate_contact').count()
    get_total_bookings_count.short_description = _('Bookings')

    def is_fulfilled(self):
        # FIXME: change to new workflow
        # if self.get_state() in [OrderState.STATE_CHOICES.cancelled,
        #                               OrderState.STATE_CHOICES.completed]:
        #     return IRRELEVANT

        result = NOT_FULFILLED
        now = timezone.now()
        today = now.date()
        next_date = self.shift_dates.filter(
            shift_date__gt=today, cancelled=False
        ).order_by('shift_date').first()

        if next_date is not None:
            result = next_date.is_fulfilled()
            if result == NOT_FULFILLED and next_date.job_offers.exists():
                unaccepted_jos = next_date.job_offers.filter(
                    status=JobOffer.STATUS_CHOICES.undefined
                )

                for unaccepted_jo in unaccepted_jos.all():
                    todays_timesheets = unaccepted_jo.time_sheets.filter(
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
        today = timezone.localtime(timezone.now()).date()
        sd_today = self.shift_dates.filter(shift_date=today, cancelled=False).first()
        if sd_today:
            result = sd_today.is_fulfilled()
        else:
            result = IRRELEVANT
        return result

    def can_fillin(self):
        not_filled_future_sd = False
        today = timezone.localtime(timezone.now()).date()
        future_sds = self.shift_dates.filter(shift_date__gte=today)
        for sd in future_sds:
            if sd.is_fulfilled() == NOT_FULFILLED:
                not_filled_future_sd = True
                break

        # FIXME: change to new workflow
        # return self.order.get_state() not in [OrderState.STATE_CHOICES.cancelled,
        #                                       OrderState.STATE_CHOICES.completed,
        #                                       OrderState.STATE_CHOICES.new] and \
        return self.is_fulfilled() in [NOT_FULFILLED, LIKELY_FULFILLED] or not_filled_future_sd

    @workflow_function
    def has_active_price_list_and_rate(self):
        today = timezone.localtime(timezone.now()).date()

        return self.customer_company.price_lists.filter(
            models.Q(
                price_list_rates__skill=self.position,
                price_list_rates__hourly_rate__gt=0
            ),
            models.Q(valid_until__gte=today) | models.Q(valid_until__isnull=True),
            effective=True, valid_from__lte=today,
        ).exists()
    has_active_price_list_and_rate.short_description = _('Customer active price list for skill')

    @workflow_function
    def is_start_date_set(self):
        return bool(self.work_start_date)
    is_start_date_set.short_description = _('Work Start Date')

    @workflow_function
    def is_default_rate_set(self):
        return self.hourly_rate_default is not None or self.hourly_rate_default <= 0
    is_default_rate_set.short_description = _('Default hourly rate')

    @workflow_function
    def is_all_sd_filled(self):
        for sd in self.shift_dates.all():
            if sd.is_fulfilled() != FULFILLED:
                return False

        return True
    is_all_sd_filled.short_description = _('Fill in all Shift Dates')

    @workflow_function
    def is_all_timesheets_approved(self):
        return not TimeSheet.objects.filter(
            job_offer__shift__date__job=self,
            supervisor_approved_at__isnull=True
        ).exists()
    is_all_timesheets_approved.short_description = _('All Time Sheets approvment')

    @workflow_function
    def is_client_active(self):
        content_type = ContentType.objects.get_for_model(core_models.CompanyRel)
        company_rel = self.customer_company.regular_companies.filter(master_company=self.provider_company).first()
        res = core_models.WorkflowObject.objects.filter(
            state__number=70, state__workflow__model=content_type, active=True, object_id=company_rel.id
        ).exists()
        return res
    is_client_active.short_description = _('Active Client')

    def after_state_created(self, workflow_object):
        if workflow_object.state.number == 20:
            sd, _ = ShiftDate.objects.get_or_create(
                job=self, shift_date=self.work_start_date,
                workers=self.workers
            )
            Shift.objects.get_or_create(date=sd, time=self.default_shift_starting_time, workers=self.workers)

            hr_utils.send_job_confirmation_sms(self)

    def save(self, *args, **kwargs):
        just_added = self._state.adding
        if just_added:
            self.provider_signed_at = timezone.now()
            existing_jobs = Job.objects.filter(
                jobsite=self.jobsite, position=self.position
            )
            completed_list = core_models.WorkflowObject.objects.filter(
                object_id__in=existing_jobs.values_list('id', flat=True), state__number=60, active=True
            ).values_list('object_id', flat=True)

            if existing_jobs.exclude(id__in=completed_list).exists():
                raise ValidationError(_('Active Job for Jobsite and Position already exist'))

        super().save(*args, **kwargs)

        if just_added and self.is_allowed(10):
            self.create_state(10)

    def get_distance_matrix(self, candidate_contact):
        """
        Get temporal and metric distance from the candidate contact to jobsite
        :param candidate_contact:
        :return: dictionary {"distance": float, "time": str, "seconds": int} or None
        """
        if self.jobsite:
            distancematrix_obj = ContactJobsiteDistanceCache.objects.filter(
                jobsite=self.jobsite, contact=candidate_contact.contact
            ).first()
            if distancematrix_obj:
                return {
                    "distance": hr_utils.meters_to_km(distancematrix_obj.distance),
                    "time": hr_utils.seconds_to_hrs(distancematrix_obj.time) if distancematrix_obj.time else 0,
                    "seconds": int(distancematrix_obj.time) if distancematrix_obj.time else -1
                }
        return None


class ShiftDate(core_models.UUIDModel):

    job = models.ForeignKey(
        Job,
        related_name="shift_dates",
        on_delete=models.CASCADE,
        verbose_name=_("Job")
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
        related_name="shift_dates",
        on_delete=models.SET_NULL,
        verbose_name=_("Hourly rate"),
        null=True,
        blank=True
    )

    cancelled = models.BooleanField(
        default=False
    )

    class Meta:
        verbose_name = _("Shift Date")
        verbose_name_plural = _("Shift Dates")

    def __str__(self):
        return '{}, {}: {}'.format(
            date_format(
                self.shift_date,
                settings.DATE_FORMAT
            ),
            _("workers"), self.workers
        )

    @property
    def job_offers(self):
        return JobOffer.objects.filter(shift__date=self)

    def is_fulfilled(self):
        result = NOT_FULFILLED
        jos = self.job_offers
        accepted_jos = jos.filter(status=JobOffer.STATUS_CHOICES.accepted)

        if jos.exists() and self.workers <= accepted_jos.count():
            result = FULFILLED
        return result
    is_fulfilled.short_description = _('Fulfilled')


class Shift(core_models.UUIDModel):
    time = models.TimeField(verbose_name=_("Time"))

    date = models.ForeignKey(
        ShiftDate,
        related_name="shifts",
        on_delete=models.CASCADE,
        verbose_name=_("Date")
    )

    workers = models.PositiveSmallIntegerField(
        verbose_name=_("Workers"),
        default=1,
        validators=[MinValueValidator(1)]
    )

    hourly_rate = models.ForeignKey(
        SkillBaseRate,
        related_name="job_shifts",
        on_delete=models.SET_NULL,
        verbose_name=_("Top hourly rate"),
        null=True,
        blank=True
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
    def job(self):
        return self.date.job

    def is_fulfilled(self):
        result = NOT_FULFILLED
        jos = self.job_offers
        accepted_jos = jos.filter(status=JobOffer.STATUS_CHOICES.accepted)

        if jos.exists() and self.workers <= accepted_jos.count():
            result = FULFILLED
        return result


class JobOffer(core_models.UUIDModel):

    sent_sms_field = 'offer_sent_by_sms'
    receive_sms_field = 'reply_received_by_sms'

    shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name='job_offers',
        verbose_name=_("Shift")
    )

    candidate_contact = models.ForeignKey(
        CandidateContact,
        verbose_name=_("Candidate contact"),
        on_delete=models.PROTECT,
        related_name='job_offers'
    )

    offer_sent_by_sms = models.ForeignKey(
        SMSMessage,
        null=True,
        blank=True,
        verbose_name=_("Offer sent by sms"),
        on_delete=models.PROTECT,
        related_name='job_offers'
    )

    reply_received_by_sms = models.ForeignKey(
        SMSMessage,
        verbose_name=_("Reply received by sms"),
        related_name='reply_job_offers',
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
        verbose_name = _("Job Offer")
        verbose_name_plural = _("Job Offers")

    def __str__(self):
        return '{}'.format(date_format(
            timezone.localtime(self.created_at), settings.DATETIME_FORMAT
        ))

    @property
    def job(self):
        return self.shift.job

    @property
    def start_time(self):
        return timezone.make_aware(
            datetime.combine(self.shift.date.shift_date, self.shift.time)
        )

    def is_accepted(self):
        return self.status == JobOffer.STATUS_CHOICES.accepted

    def is_cancelled(self):
        return self.status == JobOffer.STATUS_CHOICES.cancelled

    def is_recurring(self):
        return self.job.get_job_offers().filter(
            candidate_contact=self.candidate_contact,
            shift__date__shift_date__lt=self.shift.date.shift_date,
            status=JobOffer.STATUS_CHOICES.accepted
        ).exists()

    def is_first(self):
        return not self.job.get_job_offers().filter(
            candidate_contact=self.candidate_contact,
            shift__date__shift_date__lt=self.shift.date.shift_date
        ).exists()

    def get_future_offers(self):
        return self.job.get_job_offers().filter(
            candidate_contact=self.candidate_contact,
            shift__date__shift_date__gt=self.shift.date.shift_date
        )

    def move_candidate_to_carrier_list(self, new_offer=False, confirmed_available=None):
        if not confirmed_available:
            confirmed_available = self.is_accepted()

        cl = CarrierList.objects.filter(
            candidate_contact=self.candidate_contact, target_date=self.start_time
        ).first()

        if cl is not None:
            cl.target_date = self.start_time
            cl.confirmed_available = confirmed_available
        else:
            # TODO: uncomment after dynamic workflow upgrade
            # invalid_states = [
            #     RecruitmentStatus.STATE_CHOICES.failed,
            #     RecruitmentStatus.STATE_CHOICES.banned,
            #     RecruitmentStatus.STATE_CHOICES.suspended
            # ]
            # if self.candidate_contact.get_state() not in invalid_states:

            cl = CarrierList.objects.create(
                candidate_contact=self.candidate_contact,
                target_date=self.start_time,
                confirmed_available=confirmed_available,
                skill=self.job.position
            )

        if cl:
            if new_offer:
                cl.job_offer = self
            else:
                cl.referral_job_offer = self
                cl.job_offer = None
            cl.save()

    def get_timesheets_with_going_work_unset_or_timeout(self, check_date=None):
        now = timezone.now()
        if check_date is None:
            check_date = now.date()

        jos_with_timesheets = self.candidate_contact.job_offers.filter(
            time_sheets__shift_started_at__date=check_date,
            time_sheets__going_to_work_confirmation__isnull=True,
            time_sheets__going_to_work_sent_sms__check_reply_at__gte=now
        )
        return jos_with_timesheets

    def has_timesheets_with_going_work_unset_or_timeout(self, check_date=None):
        return self.get_timesheets_with_going_work_unset_or_timeout(check_date).exists()

    def has_future_accepted_jo(self):
        """
        Check if there are future accepted JO for the candidate/job
        :return: True or False
        """
        return self.job.get_job_offers().filter(
            candidate_contact=self.candidate_contact,
            shift__time__gt=self.shift.time,
            shift__date__shift_date__gte=self.shift.date.shift_date,
            status=self.STATUS_CHOICES.accepted
        ).exists()

    def has_previous_jo(self):
        """
        Check if there are JO for the candidate/job earlier than this one
        :return: True or False
        """
        now = timezone.now()
        return self.job.get_job_offers().filter(
            models.Q(shift__date__shift_date=now.date(), shift__time__gte=now.timetz()) |
            models.Q(shift__date__shift_date__gt=now.date()),
            models.Q(shift__date__shift_date=self.shift.date.shift_date, shift__time__lte=self.shift.time) |
            models.Q(shift__date__shift_date__lt=self.shift.date.shift_date),
            candidate_contact=self.candidate_contact,
        ).exists()

    def process_sms_reply(self, sent_sms, reply_sms, positive):
        if not (self.is_accepted() or self.is_cancelled()):
            assert isinstance(positive, bool), _('Looks like we could not decide if reply was positive')

            if self.offer_sent_by_sms == sent_sms:
                setattr(self, self.receive_sms_field, reply_sms)
                if positive:
                    self.accept('status', self.receive_sms_field, 'scheduled_sms_datetime')
                else:
                    self.cancel()

    def accept(self, *update_fields):
        self.status = JobOffer.STATUS_CHOICES.accepted
        self.scheduled_sms_datetime = None
        if update_fields:
            self.save(update_fields=update_fields)
        else:
            self.save()

        if self.is_quota_filled():
            self._cancel_for_filled_quota()

    def cancel(self):
        if self.is_accepted():
            self.move_candidate_to_carrier_list()

        self.status = self.STATUS_CHOICES.cancelled
        self.scheduled_sms_datetime = None
        self.save()

        now = timezone.now()
        time_sheet = None

        try:
            time_sheet = self.time_sheets.filter(
                job_offer__candidate_contact=self.candidate_contact,
                shift_started_at__gt=now
            ).earliest('shift_started_at')
        except TimeSheet.DoesNotExist:
            time_sheet = None

        if time_sheet is not None:
            if (time_sheet.shift_started_at - now).total_seconds() > 3600:
                from r3sourcer.apps.hr.tasks import send_job_offer_cancelled_sms
                send_job_offer_cancelled_sms.delay(self.pk)

                time_sheet.delete()
            else:
                from r3sourcer.apps.hr.tasks import send_job_offer_cancelled_lt_one_hour_sms
                send_job_offer_cancelled_lt_one_hour_sms.delay(self.pk)

                if time_sheet.going_to_work_confirmation:
                    time_sheet.auto_fill_four_hours()

    def is_quota_filled(self):
        accepted_count = self.job.get_job_offers().filter(
            status=JobOffer.STATUS_CHOICES.accepted,
            shift=self.shift
        ).count()

        return accepted_count >= self.shift.workers

    def _cancel_for_filled_quota(self):
        now = timezone.now()

        with transaction.atomic():
            # if celery worked with JO sending
            qs = self.job.get_job_offers().filter(
                models.Q(offer_sent_by_sms=None) | models.Q(time_sheets=None), shift=self.shift
            ).exclude(status=JobOffer.STATUS_CHOICES.accepted)
            jo_with_sms_sent = list(qs.filter(offer_sent_by_sms__isnull=False))
            qs.update(status=JobOffer.STATUS_CHOICES.cancelled)

            # send placement rejection sms
            for sent_jo in jo_with_sms_sent:
                if sent_jo.id == self.id:
                    continue
                if now <= sent_jo.start_time:
                    hr_utils.send_jo_rejection(sent_jo)

    def check_job_quota(self, is_initial):
        if is_initial:
            if self.is_quota_filled() or self.is_cancelled():
                now = timezone.now()
                self._cancel_for_filled_quota()
                self.move_candidate_to_carrier_list()
                self.status = JobOffer.STATUS_CHOICES.cancelled

                if now <= self.start_time:
                    hr_utils.send_jo_rejection(self)

                return False
            else:
                self.status = JobOffer.STATUS_CHOICES.accepted
                return True
        else:
            return True

    def save(self, *args, **kw):
        is_resend = kw.pop('initial', False)
        just_added = self._state.adding or is_resend
        is_initial = not self.is_recurring()
        is_accepted = self.is_accepted()

        if self.is_cancelled() and not just_added:
            orig = JobOffer.objects.get(pk=self.pk)
            if orig.is_accepted():
                orig.move_candidate_to_carrier_list(confirmed_available=True)

        if self.is_accepted() and not just_added:
            orig = JobOffer.objects.get(pk=self.pk)
            is_accepted = orig.is_accepted() != self.is_accepted()

        create_time_sheet = False
        if is_accepted:
            create_time_sheet = self.check_job_quota(is_initial)

        super(JobOffer, self).save(*args, **kw)

        if create_time_sheet:
            TimeSheet.get_or_create_for_job_offer_accepted(self)

        if just_added:
            if not self.is_cancelled() and CarrierList.objects.filter(
                    candidate_contact=self.candidate_contact,
                    target_date=self.start_time).exists():
                self.move_candidate_to_carrier_list(new_offer=True)

            task = hr_utils.get_jo_sms_sending_task(self)

            if task:
                now = timezone.localtime(timezone.now())
                tomorrow = now + timedelta(days=1)
                tomorrow_end = timezone.make_aware(datetime.combine(
                    tomorrow.date() + timedelta(days=1), time(5, 0, 0)
                ))
                target_date_and_time = timezone.localtime(self.start_time)

                # TODO: maybe need to rethink, but it should work
                # compute eta to schedule SMS sending
                if target_date_and_time <= tomorrow_end:
                    # today and tomorrow day and night shifts
                    eta = datetime.combine(now.date(), time(10, 0, 0, tzinfo=now.tzinfo))

                    if now >= target_date_and_time - timedelta(hours=1):
                        if now >= target_date_and_time + timedelta(hours=2):
                            eta = None
                        else:
                            eta = now + timedelta(seconds=10)
                    elif eta <= now or eta >= target_date_and_time - timedelta(hours=1, minutes=30):
                        eta = now + timedelta(seconds=10)
                else:
                    if not self.has_future_accepted_jo() and not self.has_previous_jo()\
                            and target_date_and_time <= now + timedelta(days=4):
                        eta = now + timedelta(seconds=10)
                    else:
                        # future date day shift
                        eta = datetime.combine(
                            target_date_and_time.date() - timedelta(days=1), time(10, 0, 0, tzinfo=now.tzinfo)
                        )
                if eta:
                    self.scheduled_sms_datetime = eta
                    self.save(update_fields=['scheduled_sms_datetime'])
                    task.apply_async(args=[self.id], eta=eta)


class TimeSheet(
        core_models.UUIDModel,
        WorkflowProcess):

    sent_sms_field = 'going_to_work_sent_sms'
    receive_sms_field = 'going_to_work_reply_sms'

    job_offer = models.ForeignKey(
        JobOffer,
        on_delete=models.CASCADE,
        related_name="time_sheets",
        verbose_name=_("Job Offer")
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
        default=hr_utils.today_7_am
    )

    break_started_at = models.DateTimeField(
        verbose_name=_("Break Started at"),
        null=True,
        blank=True,
        default=hr_utils.today_12_pm
    )

    break_ended_at = models.DateTimeField(
        verbose_name=_("Break Ended at"),
        null=True,
        blank=True,
        default=hr_utils.today_12_30_pm
    )

    shift_ended_at = models.DateTimeField(
        verbose_name=_("Shift Ended at"),
        null=True,
        blank=True,
        default=hr_utils.today_3_30_pm
    )

    supervisor = models.ForeignKey(
        core_models.CompanyContact,
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
        choices=core_models.Company.TIMESHEET_APPROVAL_SCHEME,
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
        core_models.CompanyContact,
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

    class Meta:
        verbose_name = _("Timesheet Entry")
        verbose_name_plural = _("Timesheet Entries")
        unique_together = ("job_offer", "shift_started_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__original_supervisor_id = self.supervisor_id
        self.__original_going_to_work_confirmation = self.going_to_work_confirmation
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

    def get_job_offer(self):
        return self.job_offer

    @property
    def master_company(self):
        return self.job_offer.shift.date.job.jobsite.master_company

    @property
    def regular_company(self):
        jobsite = self.job_offer.shift.date.job.jobsite
        return jobsite and jobsite.regular_company

    @classmethod
    def get_or_create_for_job_offer_accepted(cls, job_offer):
        start_time = job_offer.start_time
        data = {
            'job_offer': job_offer,
            'shift_started_at': start_time,
            'break_started_at': start_time + timedelta(hours=5),
            'break_ended_at': start_time + timedelta(hours=5, minutes=30),
            'shift_ended_at': start_time + timedelta(hours=8, minutes=30),
            'supervisor': job_offer.job.jobsite.primary_contact,
            'candidate_rate': job_offer.shift.date.hourly_rate
        }

        try:
            time_sheet, created = cls.objects.get_or_create(**data)
        except IntegrityError:
            time_sheet, created = cls.objects.update_or_create(
                job_offer=job_offer,
                shift_started_at=job_offer.start_time,
                defaults=data
            )

        now = timezone.now()
        if now <= job_offer.start_time + timedelta(hours=2):
            cls._send_placement_acceptance_sms(time_sheet, job_offer)

        return time_sheet

    @classmethod
    def _send_placement_acceptance_sms(self, time_sheet, job_offer):
        from r3sourcer.apps.hr.tasks import send_placement_acceptance_sms
        send_placement_acceptance_sms.apply_async(args=[time_sheet.id, job_offer.id], countdown=10)

    def get_closest_company(self):
        return self.get_job_offer().job.get_closest_company()

    @property
    def candidate_contact(self):
        return self.job_offer.candidate_contact

    @property
    def shift_delta(self):
        if self.shift_ended_at and self.shift_started_at:
            return self.shift_ended_at - self.shift_started_at
        return timedelta()

    @property
    def break_delta(self):
        if self.break_ended_at and self.break_started_at:
            return self.break_ended_at - self.break_started_at
        return timedelta()

    def auto_fill_four_hours(self):
        now = timezone.now()
        self.candidate_submitted_at = now
        self.supervisor_approved_at = now
        self.shift_started_at = now
        self.shift_ended_at = now + timedelta(hours=4)
        self.break_started_at = None
        self.break_ended_at = None
        self.save()

    def _send_going_to_work(self, going_eta):
        from r3sourcer.apps.hr.tasks import send_going_to_work_sms
        send_going_to_work_sms.apply_async(args=[self.pk], eta=going_eta)

    def _send_submit_sms(self, going_eta):
        from r3sourcer.apps.hr.tasks import process_time_sheet_log_and_send_notifications, SHIFT_ENDING
        process_time_sheet_log_and_send_notifications.apply_async(args=[self.pk, SHIFT_ENDING], eta=going_eta)

    def process_sms_reply(self, sent_sms, reply_sms, positive):
        if self.going_to_work_confirmation is None:
            assert isinstance(positive, bool), _('Looks like we could not decide if reply was positive')
            if self.going_to_work_sent_sms == sent_sms:
                self.going_to_work_reply_sms = reply_sms
                self.going_to_work_confirmation = positive
                self.save()

    def save(self, *args, **kwargs):
        just_added = self._state.adding
        going_set = self.going_to_work_confirmation is not None and (
            just_added or self.__original_going_to_work_confirmation != self.going_to_work_confirmation
        )
        candidate_submitted_at = self.candidate_submitted_at is not None and (
            just_added or self.__original_candidate_submitted_at != self.candidate_submitted_at
        )
        if just_added:
            if not self.supervisor and self.job_offer:
                self.supervisor = self.job_offer.job.jobsite.primary_contact

            now = timezone.now()
            if now <= self.shift_started_at:
                going_eta = self.shift_started_at - timedelta(minutes=settings.GOING_TO_WORK_SMS_DELAY_MINUTES)
                if going_eta > now:
                    self._send_going_to_work(going_eta)
                else:
                    self.going_to_work_confirmation = True

        super(TimeSheet, self).save(*args, **kwargs)

        if just_added and self.is_allowed(10):
            self.create_state(10)

        if going_set and self.going_to_work_confirmation and self.is_allowed(20):
            self.create_state(20)
            self._send_submit_sms(self.shift_ended_at)

        if not just_added:
            if self.candidate_submitted_at is not None and self.is_allowed(30):
                self.create_state(30)
            if self.supervisor_approved_at is not None and self.is_allowed(40):
                self.create_state(40)
            if self.is_allowed(70):
                self.create_state(70)

        # If accepted manually, disable reply checking.
        if self.going_to_work_confirmation and self.going_to_work_sent_sms and self.going_to_work_sent_sms.check_reply:
            self.going_to_work_sent_sms.no_check_reply()
        self.__original_supervisor_id = self.supervisor_id
        self.__original_going_to_work_confirmation = self.going_to_work_confirmation
        self.__original_candidate_submitted_at = self.candidate_submitted_at

        if candidate_submitted_at and self.supervisor and not self.supervisor_approved_at:
            hr_utils.send_supervisor_timesheet_approve(self)


class TimeSheetIssue(
        core_models.UUIDModel,
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
        core_models.CompanyContact,
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
        core_models.CompanyContact,
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


class BlackList(core_models.UUIDModel):

    company = models.ForeignKey(
        core_models.Company,
        related_name="blacklists",
        on_delete=models.CASCADE,
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
        core_models.CompanyContact,
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
            self.jobsite = self.timesheet.job_offer.job.jobsite
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

    @classmethod
    def owned_by_lookups(cls, owner):
        if isinstance(owner, core_models.Company):
            return [
                models.Q(company=owner),
                models.Q(company__regular_companies__master_company=owner)
            ]


class FavouriteList(core_models.UUIDModel):

    company_contact = models.ForeignKey(
        core_models.CompanyContact,
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
        core_models.Company,
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

    job = models.ForeignKey(
        Job,
        verbose_name=_('Job'),
        related_name='favouritelists',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _("Favourite list")
        verbose_name_plural = _("Favourite lists")
        unique_together = ('company_contact', 'candidate_contact', 'company', 'jobsite', 'job')

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

        if self.job:
            self.jobsite = self.job.jobsite
        if self.jobsite:
            self.company = self.jobsite.master_company
        if FavouriteList.objects.filter(
            company_contact=self.company_contact,
            candidate_contact=self.candidate_contact,
            company=self.company,
            jobsite=self.jobsite,
            job=self.job,
        ).exists() and not (self.company and self.jobsite and self.job):
            raise ValidationError(_('Another FavoritList item with such parameters already exists'))
        super().clean()

    @classmethod
    def owned_by_lookups(cls, owner):
        if isinstance(owner, core_models.Company):
            return [
                models.Q(company=owner),
                models.Q(company__regular_companies__master_company=owner)
            ]


class CarrierList(core_models.UUIDModel):

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
        default=hr_utils.tomorrow
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

    job_offer = models.ForeignKey(
        JobOffer,
        verbose_name=_('Job Offer'),
        related_name='carrier_lists',
        blank=True,
        null=True
    )

    referral_job_offer = models.ForeignKey(
        JobOffer,
        verbose_name=_('Referral Job Offer'),
        related_name='referral_carrier_lists',
        blank=True,
        null=True
    )

    sms_sending_scheduled_at = models.DateTimeField(
        verbose_name=_("SMS sending scheduled at"),
        null=True,
        blank=True
    )

    skill = models.ForeignKey(
        Skill,
        verbose_name=_('Skill'),
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


class CandidateEvaluation(core_models.UUIDModel):

    candidate_contact = models.ForeignKey(
        CandidateContact,
        on_delete=models.PROTECT,
        related_name="candidate_evaluations",
        verbose_name=_("Candidate Contact")
    )

    supervisor = models.ForeignKey(
        core_models.CompanyContact,
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


class ContactJobsiteDistanceCache(core_models.UUIDModel):
    contact = models.ForeignKey(
        core_models.Contact,
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

    distance = models.IntegerField()

    time = models.IntegerField(null=True, blank=True)

    updated_at = models.DateTimeField(
        verbose_name=_("Updated at"),
        auto_now=True,
        editable=False,
        null=True
    )

    class Meta:
        unique_together = ("contact", "jobsite")


class Payslip(core_models.UUIDModel):

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
        core_models.Company,
        on_delete=models.SET_NULL,
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


class PayslipRule(core_models.AbstractPayRuleMixin, core_models.UUIDModel):

    company = models.ForeignKey(
        core_models.Company,
        related_name="payslip_rules",
        verbose_name=_("Company"),
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _("Payslip Rule")
        verbose_name_plural = _("Payslip Rules")


class PayslipLine(core_models.UUIDModel):

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


class PersonalIncomeTax(core_models.UUIDModel):

    country = models.ForeignKey(
        core_models.Country,
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


class SocialInsurance(core_models.UUIDModel):

    country = models.ForeignKey(
        core_models.Country,
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


class CandidateScore(core_models.UUIDModel):

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

    average_score = models.DecimalField(
        decimal_places=2,
        max_digits=3,
        verbose_name=_("Average Score"),
        null=True,
        editable=False
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
        jos = JobOffer.objects.filter(
            candidate_contact=self.candidate_contact
        )
        accepted_jos = jos.filter(
            status=JobOffer.STATUS_CHOICES.accepted
        ).count()
        cancelled_jos = endless_logger.get_history_object_ids(
            JobOffer, 'status', '2', ids=jos.values_list('id', flat=True)
        )
        absent_jos = len(endless_logger.get_history_object_ids(
            JobOffer, 'status', '1', ids=cancelled_jos
        ))

        total_jos = accepted_jos + absent_jos

        reliability = (
            5 * (accepted_jos / total_jos) if total_jos > 4 else 0
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
        jos = JobOffer.objects.filter(
            candidate_contact=self.candidate_contact
        )
        accepted_jos = jos.filter(
            status=JobOffer.STATUS_CHOICES.accepted
        )

        # Calculate shift acceptance
        loyalty = self.recalc_reliability(False)

        # Calculate time bonus
        time_shift = timedelta(hours=1, minutes=30)
        time_bonus = len(endless_logger.get_history_object_ids(
            JobOffer, 'status', '1', ids=jos.values_list('id', flat=True)
        ))
        time_bonus = accepted_jos.filter(
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
            jobsite__in=jos.values_list(
                'shift__date__job__jobsite', flat=True
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
        company = self.candidate_contact.get_closest_company()

        score_sum = sum([s.get_score(self.candidate_contact, company) for s in states])

        if len(states) > 0:
            self.recruitment_score = score_sum / len(states)

    def recalc_scores(self):
        self.recalc_client_feedback()
        self.recalc_reliability()
        self.recalc_loyalty()
        self.recalc_recruitment_score()
        self.average_score = self.get_average_score()
        self.save()

    def get_average_score(self):
        if not self.average_score:
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
            self.average_score = total_score / scores_count if scores_count else None
            self.save(update_fields=['average_score'])

        return self.average_score


class JobTag(core_models.UUIDModel):
    tag = models.ForeignKey(
        core_models.Tag,
        related_name="job_tags",
        on_delete=models.PROTECT,
        verbose_name=_("Tag")
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.PROTECT,
        related_name="tags",
        verbose_name=_("Job")
    )

    class Meta:
        verbose_name = _("Job Tag")
        verbose_name_plural = _("Job Tags")
        unique_together = ("tag", "job")

    def __str__(self):
        return self.tag.name
