from datetime import timedelta

from crum import get_current_request
from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from phonenumber_field.modelfields import PhoneNumberField

from r3sourcer import ref
from r3sourcer.apps.activity.models import Activity
from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.decorators import workflow_function
from r3sourcer.apps.core.utils.companies import get_site_master_company
from r3sourcer.apps.core.utils.user import get_default_user
from r3sourcer.apps.core.workflow import WorkflowProcess


class VisaType(core_models.UUIDModel):

    GENERAL_TYPE_CHOICES = Choices(
        ('visitor', _("Visitor")),
        ('working', _("Working and Skilled")),
        ('studying', _("Studying")),
        ('family', _("Family and Spousal")),
        ('refugee', _("Refugee and Humanitarian")),
        ('other', _("Other")),
        ('repealed', _("Repealed")),
        ('temp', _("Temporary")),
        ('temp_resid', _("Temporary Resident")),
        ('bridging', _("Bridging Visa")),
    )

    subclass = models.CharField(
        max_length=4,
        verbose_name=_("Subclass Number"),
        unique=True
    )

    name = models.CharField(
        max_length=255,
        verbose_name=_("Visa Type Name")
    )

    general_type = models.CharField(
        max_length=10,
        verbose_name=_("General Visa Type"),
        choices=GENERAL_TYPE_CHOICES,
        default=GENERAL_TYPE_CHOICES.other
    )

    work_hours_allowed = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Working Hours Allowed")
    )

    is_available = models.BooleanField(
        default=True,
        verbose_name=_("Available")
    )

    class Meta:
        verbose_name = _("Visa Type")
        verbose_name_plural = _("Visa Types")

    def __str__(self):
        return '{}: {} ({})'.format(
            self.subclass, self.name, self.general_type
        )

    @classmethod
    def is_owned(cls):
        return False


class SuperannuationFund(core_models.UUIDModel):

    fund_name = models.CharField(
        max_length=255,
        verbose_name=_('Name')
    )

    abn = models.CharField(
        max_length=16,
        verbose_name=_("ABN")
    )

    usi = models.CharField(
        max_length=16,
        verbose_name=_("USI")
    )

    product_name = models.CharField(
        max_length=255,
        verbose_name=_("Product Name")
    )

    contribution_restrictions = models.BooleanField(
        verbose_name=_("Contribution Restrictions")
    )

    from_date = models.DateField(
        verbose_name=_("From Date")
    )

    to_date = models.DateField(
        verbose_name=_("To Date")
    )

    class Meta:
        verbose_name = _("Superannuation Fund")
        verbose_name_plural = _("Superannuation Funds")
        unique_together = ('product_name', 'abn', 'usi')

    def __str__(self):
        return self.product_name

    @classmethod
    def is_owned(cls):
        return False


class CandidateContact(core_models.UUIDModel, WorkflowProcess):

    RESIDENCY_STATUS_CHOICES = Choices(
        (0, 'unknown', _('Unknown')),
        (1, 'citizen', _('Citizen')),
        (2, 'permanent', _('Permanent Resident')),
        (3, 'temporary', _('Temporary Resident')),
    )

    REFERRAL_CHOICES = Choices(
        (0, 'other', _("Other / Unspecified")),
        (1, 'direct', _("Direct Contact")),
        (2, 'friend', _("Friend")),
        (3, 'internet', _("Internet Search")),
        (4, 'RTO', _("RTO")),
        (5, 'job_agent', _("Job Agent")),
        (6, 'advertisement', _("Advertisement")),
    )

    TRANSPORTATION_CHOICES = Choices(
        (1, 'own', _("Own Car")),
        (2, 'public', _("Public Transportation")),
    )

    contact = models.OneToOneField(
        'core.Contact',
        on_delete=models.CASCADE,
        related_name="candidate_contacts",
        verbose_name=_("Contact")
    )

    recruitment_agent = models.ForeignKey(
        'core.CompanyContact',
        null=True,
        blank=True,
        related_name='candidate_contacts',
        verbose_name=_('Recruitment agent'),
        on_delete=models.PROTECT
    )

    residency = models.PositiveSmallIntegerField(
        verbose_name=_("Residency Status"),
        choices=RESIDENCY_STATUS_CHOICES,
        default=RESIDENCY_STATUS_CHOICES.unknown
    )

    nationality = models.ForeignKey(
        'core.Country',
        to_field='code2',
        null=True,
        blank=True,
        related_name="candidate_contacts"
    )

    visa_type = models.ForeignKey(
        'candidate.VisaType',
        null=True,
        blank=True,
        related_name="candidate_contacts",
        verbose_name=_("Visa Type"),
        on_delete=models.PROTECT
    )

    visa_expiry_date = models.DateField(
        verbose_name=_("Visa Expiry Date"),
        blank=True,
        null=True
    )

    vevo_checked_at = models.DateField(
        verbose_name=_("VEVO checked at"),
        blank=True,
        null=True
    )

    referral = models.PositiveSmallIntegerField(
        verbose_name=_("Referral Source"),
        choices=REFERRAL_CHOICES,
        default=REFERRAL_CHOICES.direct
    )

    tax_file_number = models.CharField(
        max_length=9,
        verbose_name=_("Tax File Number"),
        blank=True
    )

    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("Weight, kg"),
        null=True,
        blank=True
    )

    height = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("Height, cm"),
        null=True,
        blank=True
    )

    strength = models.PositiveSmallIntegerField(
        verbose_name=_("Strength"),
        default=0
    )

    language = models.PositiveSmallIntegerField(
        verbose_name=_("Language"),
        default=0
    )

    transportation_to_work = models.PositiveSmallIntegerField(
        choices=TRANSPORTATION_CHOICES,
        verbose_name=_("Transportation to Work"),
        null=True,
        blank=True
    )

    emergency_contact_name = models.CharField(
        max_length=63,
        verbose_name=_("Emergency Contact Name"),
        blank=True
    )

    emergency_contact_phone = PhoneNumberField(
        verbose_name=_("Emergency Contact Phone Number"),
        blank=True
    )

    autoreceives_sms = models.BooleanField(
        verbose_name=_("Autoreceives SMS"),
        default=True
    )

    message_by_sms = models.BooleanField(
        default=True,
        verbose_name=_('By SMS')
    )

    message_by_email = models.BooleanField(
        default=True,
        verbose_name=_('By E-Mail')
    )

    bank_account = models.ForeignKey(
        'core.BankAccount',
        related_name="candidates",
        on_delete=models.PROTECT,
        verbose_name=_("Bank Account"),
        blank=True,
        null=True
    )

    employment_classification = models.ForeignKey(
        'skills.EmploymentClassification',
        related_name="candidates",
        on_delete=models.PROTECT,
        verbose_name=_("Employment Classification"),
        blank=True,
        null=True
    )

    superannuation_fund = models.ForeignKey(
        'candidate.SuperannuationFund',
        related_name="candidates",
        on_delete=models.PROTECT,
        verbose_name=_("Superannuation Fund"),
        blank=True,
        null=True
    )

    superannuation_membership_number = models.CharField(
        max_length=255,
        verbose_name=_("Employee Membership Number"),
        blank=True,
        null=True
    )

    profile_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("Profile Price"),
        default=0
    )

    class Meta:
        verbose_name = _("Candidate Contact")
        verbose_name_plural = _("Candidate Contacts")

    def __str__(self):
        return str(self.contact)

    @property
    def notes(self):
        return core_models.Note.objects.filter(
            content_type__model=self.__class__.__name__.lower(),
            object_id=self.pk
        )

    @property
    def activities(self):
        return Activity.objects.filter(
            entity_object_name=self.__class__.__name__,
            entity_object_id=self.pk
        )

    # REQUIREMENTS AND ACTIONS FOR WORKFLOW
    @workflow_function
    def is_skill_defined(self):
        return self.candidate_skills.filter(skill__active=True).count() > 0
    is_skill_defined.short_description = _("Define at least one skill")

    @workflow_function
    def is_skill_score_defined(self):
        return self.candidate_skills.filter(score__gt=0, skill__active=True).count() > 0
    is_skill_score_defined.short_description = _("At least one active skill score must be higher that 0")

    @workflow_function
    def is_skill_rate_defined(self):
        return self.candidate_skills.filter(score__gt=0, skill__active=True, hourly_rate__gt=0).count() > 0
    is_skill_rate_defined.short_description = _("At least one active skill hourly rate must be higher that 0")

    @workflow_function
    def is_personal_info_filled(self):
        return bool(self.height is not None and
                    self.weight is not None and
                    self.transportation_to_work is not None)
    is_personal_info_filled.short_description = _(
        'Height, weight, transportation to work'
    )

    @workflow_function
    def is_contact_info_filled(self):
        return bool(self.contact.first_name and
                    self.contact.last_name and
                    self.contact.title and
                    self.contact.email and
                    self.contact.phone_mobile)
    is_contact_info_filled.short_description = _(
        'Contact\'s title, first name, '
        'last name, email and mobile phone '
        'must be filled.'
    )

    @workflow_function
    def is_formalities_filled(self):
        return bool(self.tax_file_number and
                    self.superannuation_fund and
                    self.superannuation_membership_number and
                    self.bank_account and
                    self.emergency_contact_name and
                    self.emergency_contact_phone)
    is_formalities_filled.short_description = _(
        'All formalities info is required'
    )

    @workflow_function
    def is_residency_filled(self):
        residency_list = [self.RESIDENCY_STATUS_CHOICES.citizen,
                          self.RESIDENCY_STATUS_CHOICES.permanent]
        if self.residency in residency_list:
            return True
        elif (self.visa_type and self.visa_expiry_date and
                self.vevo_checked_at and self.nationality):
            return True
        return False
    is_residency_filled.short_description = _('All residency info is required')

    @workflow_function
    def are_skill_rates_set(self):
        for skill in self.candidate_skills.filter(score__gt=0, skill__active=True).all():
            if not skill.get_valid_rate():
                return False
        return True
    are_skill_rates_set.short_description = _(
        'Valid hourly rate for each assigned skill must be set.')

    @workflow_function
    def are_tags_verified(self):
        for tag in self.tag_rels.all():
            if not tag.verified_by:
                return False
        return True
    are_tags_verified.short_description = _('All tags must be verified.')

    @workflow_function
    def is_address_set(self):
        return bool(self.contact.address and
                    self.contact.address.street_address and
                    self.contact.address.city and
                    self.contact.address.postal_code and
                    self.contact.address.state)
    is_address_set.short_description = _('Address must be set.')

    @workflow_function
    def is_email_set(self):
        return bool(self.contact.email)
    is_email_set.short_description = _('Email must be set.')

    @workflow_function
    def is_phone_set(self):
        return bool(self.contact.phone_mobile)
    is_phone_set.short_description = _('Mobile Phone must be set.')

    @workflow_function
    def is_birthday_set(self):
        return bool(self.contact.birthday)
    is_birthday_set.short_description = _('Birthday must be set.')

    @workflow_function
    def is_email_verified(self):
        return self.contact.email_verified
    is_email_verified.short_description = _('Verified e-mail')

    @workflow_function
    def is_phone_verified(self):
        return self.contact.phone_mobile_verified
    is_phone_verified.short_description = _('Verified mobile phone')

    def get_bmi(self):
        if self.weight and self.height:
            height = self.height if self.height < 3.0 else self.height / 100
            bmi = self.weight / (height ** 2)
            if bmi > 25:
                return _("Over Weight")
            elif bmi > 18.5:
                return _("Normal Weight")
            else:
                return _("Under Weight")
        return None

    def set_contact_unavailable(self):
        """
        Sets available to False
        """
        self.contact.is_available = False
        self.contact.save()

    def get_phone_mobile(self):
        if self.autoreceives_sms and self.contact.phone_mobile:
            return self.contact.phone_mobile
        return None

    def get_email(self):
        return self.contact.email

    def get_candidate_rate_for_skill(self, skill, **skill_kwargs):
        candidate_skill = self.candidate_skills.filter(
            skill=skill, **skill_kwargs
        ).first()
        if candidate_skill:
            candidate_skill_rate = candidate_skill.get_valid_rate()
            if candidate_skill_rate:
                return candidate_skill_rate
        return None

    def get_closest_company(self):
        try:
            current_request = get_current_request()
            company_qry = models.Q()

            if current_request and current_request.user.is_authenticated:
                current_user = current_request.user
                if current_user.contact.is_company_contact():
                    current_company = current_user.contact.get_closest_company()
                    company_qry = models.Q(master_company=current_company)

            candidate_rel = self.candidate_rels.filter(company_qry, owner=True, active=True).first()
            if not candidate_rel:
                candidate_rel = self.candidate_rels.get(
                    master_company__type=core_models.Company.COMPANY_TYPES.master, owner=True)

            return candidate_rel.master_company
        except CandidateRel.DoesNotExist:
            return get_site_master_company()

    def save(self, *args, **kwargs):
        just_added = self._state.adding
        super().save(*args, **kwargs)

        if just_added:

            self.contact.user.role.add(core_models.Role.objects.create(name=core_models.Role.ROLE_NAMES.candidate))

            if not hasattr(self, 'candidate_scores'):
                from r3sourcer.apps.hr.models import CandidateScore
                obj = CandidateScore.objects.create(candidate_contact=self)
                obj.recalc_scores()

            self.create_state(10)

    def process_sms_reply(self, sent_sms, reply_sms, positive):
        related_objs = reply_sms.get_related_objects()

        for related_object in related_objs:
            if isinstance(related_object, core_models.WorkflowObject):
                self._process_sms_workflow_object(related_object)

    def _process_sms_workflow_object(self, workflow_object):
        if workflow_object.state.number == 11:
            workflow_object.active = True
            workflow_object.save(update_fields=['active'])

    def before_state_creation(self, workflow_object):
        if workflow_object.state.number == 11:  # Phone verify
            workflow_object.active = False

    def after_state_created(self, workflow_object):
        if workflow_object.state.number == 11:  # Phone verify
            workflow_object.active = True

        self.candidate_scores.recalc_scores()

    def get_rate_for_skill(self, skill, **skill_kwargs):
        """
        :param skill: pepro.crm_hr.models.Skill
        :return: pepro.crm_hr.models.SkillBaseRate or None
        """
        candidate_skill = self.candidate_skills.filter(skill=skill, **skill_kwargs).first()
        if candidate_skill:
            candidate_skill_rate = candidate_skill.get_valid_rate()
            if candidate_skill_rate:
                return candidate_skill_rate
        return None

    @classmethod
    def owned_by_lookups(cls, owner):
        if isinstance(owner, core_models.Company):
            return [
                models.Q(candidate_rels__master_company=owner)
            ]


class TagRel(core_models.UUIDModel):
    tag = models.ForeignKey(
        'core.Tag',
        related_name="tag_rels",
        on_delete=models.PROTECT,
        verbose_name=_("Tag")
    )

    candidate_contact = models.ForeignKey(
        'candidate.CandidateContact',
        on_delete=models.CASCADE,
        related_name="tag_rels",
        verbose_name=_("Candidate Contact")
    )

    def verification_evidence_path(self, filename):
        return 'candidates/tags/{}/{}'.format(self.id, filename)

    verification_evidence = models.FileField(
        verbose_name=_("Verification Evidence"),
        upload_to=verification_evidence_path,
        null=True,
        blank=True
    )

    verified_by = models.ForeignKey(
        'core.CompanyContact',
        on_delete=models.PROTECT,
        related_name="verified_tag_rels",
        verbose_name=_("Verified By"),
        blank=True,
        null=True
    )

    verify = True

    class Meta:
        verbose_name = _("Tag Relationship")
        verbose_name_plural = _("Tag Relationships")
        unique_together = ("tag", "candidate_contact")

    def __str__(self):
        return self.tag.name

    def save(self, *args, **kwargs):
        # we don't allow set verified_by if tag require evidence
        # approval and this approval not uploaded
        if self.tag.evidence_required_for_approval and not self.verification_evidence:
            self.verified_by = None
            self.verify = False
        if self.verify:
            request = get_current_request()
            if request and request.user and request.user.is_authenticated():
                default_user = request.user
            else:
                default_user = get_default_user()
            if core_models.CompanyContact.objects.filter(
                    contact__user=default_user).exists():
                self.verified_by = core_models.CompanyContact.objects.filter(
                    contact__user=default_user
                ).first()
        else:
            self.verified_by = None
        super(TagRel, self).save(*args, **kwargs)

    @classmethod
    def is_owned(cls):
        return False


class SkillRel(core_models.UUIDModel):

    PRIOR_EXPERIENCE_CHOICES = Choices(
        (timedelta(days=0), 'inexperienced', _("Inexperienced")),
        (timedelta(days=30), "1month", _("1 Month")),
        (timedelta(days=90), "3months", _("3 Months")),
        (timedelta(days=180), "6months", _("6 Months")),
        (timedelta(days=365), "1year", _("1 Year")),
        (timedelta(days=730), "2years", _("2 Years")),
        (timedelta(days=1095), "3years", _("3 Years")),
        (timedelta(days=1825), "5years", _("5 Years or more")),
    )

    skill = models.ForeignKey(
        'skills.Skill',
        related_name="candidate_skills",
        verbose_name=_("Skill")
    )

    score = models.PositiveSmallIntegerField(
        verbose_name=_("Score"),
        default=0
    )

    candidate_contact = models.ForeignKey(
        'candidate.CandidateContact',
        on_delete=models.CASCADE,
        related_name="candidate_skills"
    )

    prior_experience = models.DurationField(
        verbose_name=_("Prior Experience"),
        choices=PRIOR_EXPERIENCE_CHOICES,
        default=PRIOR_EXPERIENCE_CHOICES.inexperienced
    )

    hourly_rate = models.DecimalField(
        decimal_places=2,
        max_digits=8,
        verbose_name=_("Skill Rate"),
    )

    class Meta:
        verbose_name = _("Candidate Skill")
        verbose_name_plural = _("Candidate Skills")
        unique_together = ("skill", "candidate_contact")

    def __str__(self):
        return '{}: {} ({}*)'.format(
            str(self.candidate_contact), str(self.skill), str(self.score))

    def get_valid_rate(self):
        return self.hourly_rate

    def get_myob_name(self):
        return '{} {}'.format(str(self.skill.get_myob_name()), str(self.hourly_rate))

    @classmethod
    def is_owned(cls):
        return False

    def save(self, *args, **kwargs):
        if self._state.adding:
            if not self.hourly_rate:
                self.hourly_rate = self.skill.default_rate or 0

        super().save(*args, **kwargs)

        self.candidate_contact.candidate_scores.recalc_scores()


class SkillRateCoefficientRel(core_models.UUIDModel):
    skill_rel = models.ForeignKey(
        'candidate.SkillRel',
        related_name="candidate_skill_coefficient_rels",
        verbose_name=_("Candidate skill")
    )

    rate_coefficient = models.ForeignKey(
        'pricing.RateCoefficient',
        related_name="candidate_skill_coefficient_rels",
        verbose_name=_("Rate coefficient")
    )

    rate_coefficient_modifier = models.ForeignKey(
        'pricing.RateCoefficientModifier',
        related_name="candidate_skill_coefficient_rels",
        verbose_name=_("Rate coefficient modifier")
    )

    class Meta:
        verbose_name = _("Candidate Skill Rate Coefficient Relation")
        verbose_name_plural = _("Candidate Skill Rate Coefficient Relations")
        unique_together = ("skill_rel", "rate_coefficient", "rate_coefficient_modifier")


class InterviewSchedule(core_models.TimeZoneUUIDModel):
    CATEGORY_CHOICES = Choices(
        ('first_phone_interview', _('First Phone Interview')),
        ('second_phone_interview', _('Second Phone Interview')),
        ('live_interview', _('Live interview')),
    )

    candidate_contact = models.ForeignKey(
        'candidate.CandidateContact',
        on_delete=models.PROTECT,
        related_name="interview_schedules",
        verbose_name=_("Candidate Contact")
    )

    company_contact = models.ForeignKey(
        'core.CompanyContact',
        related_name="interview_schedules",
        on_delete=models.PROTECT,
        verbose_name=_("Company Contact")
    )

    target_date_and_time = ref.DTField(verbose_name=_("Target date"))

    category = models.CharField(
        max_length=15,
        verbose_name=_("Category"),
        choices=CATEGORY_CHOICES,
        null=True,
        blank=True
    )

    accepted = models.BooleanField(default=False, verbose_name=_("Accepted"))

    @property
    def geo(self):
        raise NotImplementedError

    @property
    def target_date_and_time_tz(self):
        return self.utc2local(self.target_date_and_time)

    @property
    def target_date_and_time_utc(self):
        return self.target_date_and_time

    def __str__(self):
        return "{}: {}".format(self.candidate_contact,
                               self.target_date_and_time)


class CandidateRel(core_models.UUIDModel):

    candidate_contact = models.ForeignKey(
        'candidate.CandidateContact',
        on_delete=models.CASCADE,
        related_name="candidate_rels",
        verbose_name=_("Candidate Contact")
    )

    master_company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name="candidate_rels",
        verbose_name=_("Master Company")
    )

    company_contact = models.ForeignKey(
        'core.CompanyContact',
        related_name="candidate_rels",
        on_delete=models.CASCADE,
        verbose_name=_("Company Contact"),
        blank=True,
        null=True
    )

    owner = models.BooleanField(
        default=False,
        verbose_name=_("Is owner")
    )

    active = models.BooleanField(
        default=True,
        verbose_name=_("Active")
    )

    class Meta:
        verbose_name = _("Candidate Relationship")
        verbose_name_plural = _("Candidate Relationships")

    def __str__(self):
        return "{}: {}".format(self.master_company, self.candidate_contact)


class AcceptanceTestRel(core_models.TimeZoneUUIDModel):

    acceptance_test = models.ForeignKey(
        'acceptance_tests.AcceptanceTest',
        on_delete=models.CASCADE,
        related_name='candidate_acceptance_tests',
        verbose_name=_("Acceptance Test")
    )

    candidate_contact = models.ForeignKey(
        'candidate.CandidateContact',
        on_delete=models.CASCADE,
        related_name='candidate_acceptance_tests',
        verbose_name=_("Candidate Contact")
    )

    test_started_at = ref.DTField(verbose_name=_("Test Started at"))
    test_finished_at = ref.DTField(verbose_name=_("Test Finished at"))

    class Meta:
        verbose_name = _("Acceptance Test Relation")
        verbose_name_plural = _("Acceptance Test Relations")

    @property
    def geo(self):
        raise NotImplementedError

    @property
    def test_started_at_tz(self):
        return self.utc2local(self.test_started_at)

    @property
    def test_started_at_utc(self):
        return self.test_started_at

    @property
    def test_finished_at_tz(self):
        return self.utc2local(self.test_finished_at)

    @property
    def test_finished_at_utc(self):
        return self.test_finished_at

    def __str__(self):
        return '{} {}'.format(
            str(self.candidate_contact), str(self.acceptance_test)
        )

    def save(self, *args, **kwargs):
        if not self.test_started_at:
            self.test_started_at = self.now_utc
        self.test_finished_at = self.now_utc
        super().save(*args, **kwargs)


class AcceptanceTestQuestionRel(core_models.TimeZoneUUIDModel):

    candidate_acceptance_test = models.ForeignKey(
        'candidate.AcceptanceTestRel',
        on_delete=models.CASCADE,
        related_name='acceptance_test_question_rels',
        verbose_name=_("Acceptance Test Relation")
    )

    acceptance_test_question = models.ForeignKey(
        'acceptance_tests.AcceptanceTestQuestion',
        on_delete=models.PROTECT,
        related_name='acceptance_test_question_rels',
        verbose_name=_("Acceptance Test Question")
    )

    acceptance_test_answer = models.ForeignKey(
        'acceptance_tests.AcceptanceTestAnswer',
        on_delete=models.PROTECT,
        related_name='acceptance_test_question_rels',
        verbose_name=_("Acceptance Test Answer")
    )

    question_answered_at = ref.DTField(verbose_name=_("Question Answered at"))

    class Meta:
        verbose_name = _("Acceptance Test Question Relation")
        verbose_name_plural = _("Acceptance Test Question Relations")

    @property
    def geo(self):
        raise NotImplementedError

    @property
    def question_answered_at_tz(self):
        return self.utc2local(self.question_answered_at)

    @property
    def question_answered_at_utc(self):
        return self.question_answered_at

    def __str__(self):
        return '{}, {}: {}'.format(str(self.candidate_acceptance_test),
                                   str(self.acceptance_test_question),
                                   str(self.acceptance_test_answer))

    def get_if_correct(self):
        return self.acceptance_test_answer in \
               self.acceptance_test_question.get_correct_answers()

    def save(self, *args, **kwargs):
        self.question_answered_at = self.now_utc
        super().save(*args, **kwargs)


class Subcontractor(core_models.UUIDModel):

    SUBCONTRACTOR_TYPE_CHOICES = Choices(
        (10, 'sole_trader', _("sole_trader")),
        (20, 'company', _("company")),
    )

    subcontractor_type = models.PositiveSmallIntegerField(
        verbose_name=_("Subcontractor Type"),
        choices=SUBCONTRACTOR_TYPE_CHOICES,
        default=SUBCONTRACTOR_TYPE_CHOICES.sole_trader
    )

    business_id = models.CharField(
        max_length=31,
        verbose_name=_("Business Number")
    )

    company = models.OneToOneField(
        core_models.Company,
        on_delete=models.CASCADE,
        parent_link=True,
        null=True,
        blank=True
    )

    primary_contact = models.ForeignKey(
        'candidate.CandidateContact',
        verbose_name=_('Candidate Contact'),
        on_delete=models.CASCADE
    )

    allowance_enabled = models.BooleanField(
        verbose_name=_('Allowance Enabled'),
        default=False
    )

    penalty_rates_enabled = models.BooleanField(
        verbose_name=_('Penalty Rates Enabled'),
        default=False
    )

    class Meta:
        verbose_name = _("Subcontractor")
        verbose_name_plural = _("Subcontractors")

    def __str__(self):
        if self.subcontractor_type == self.SUBCONTRACTOR_TYPE_CHOICES.sole_trader:
            return str(self.primary_contact)
        return str(self.company)


class SubcontractorCandidateRelation(core_models.UUIDModel):

    subcontractor = models.ForeignKey(
        'candidate.Subcontractor',
        related_name='subcontractor_candidates',
        verbose_name=_('Subcontractor')
    )

    candidate_contact = models.ForeignKey(
        'candidate.CandidateContact',
        related_name='subcontractor_candidates',
        verbose_name=_('Candidate Contact')
    )

    class Meta:
        verbose_name = _("Subcontractor Candidate Relation")
        verbose_name_plural = _("Subcontractor Candidate Relations")


class CandidateContactAnonymous(CandidateContact):

    class Meta:
        proxy = True

    def __str__(self):
        return 'Anonymous Candidate'
