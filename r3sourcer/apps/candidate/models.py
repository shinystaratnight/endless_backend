from datetime import timedelta

from django.core.cache import cache
from django.db import models
from django.utils.translation import ugettext_lazy as _

from crum import get_current_request
from model_utils import Choices
from phonenumber_field.modelfields import PhoneNumberField

from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.utils.companies import get_site_master_company
from r3sourcer.apps.core.workflow import WorkflowProcess
from r3sourcer.apps.skills import models as skill_models
from r3sourcer.apps.core.decorators import workflow_function
from r3sourcer.apps.activity import models as activity_models
from r3sourcer.apps.acceptance_tests import models as acceptance_test_models
from r3sourcer.apps.core.utils.user import get_default_user


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


class SuperannuationFund(core_models.UUIDModel):

    name = models.CharField(
        max_length=76,
        verbose_name=_('Name')
    )

    membership_number = models.CharField(
        max_length=255,
        verbose_name=_("Employer Membership Number"),
        blank=True,
        null=True
    )

    phone = PhoneNumberField(
        verbose_name=_("Phone Number"),
        blank=True,
        null=True
    )

    website = models.CharField(
        max_length=255,
        verbose_name=_("Website"),
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _("Superannuation Fund")
        verbose_name_plural = _("Superannuation Funds")

    def __str__(self):
        return self.name


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
        core_models.Contact,
        on_delete=models.CASCADE,
        related_name="candidate_contacts",
        verbose_name=_("Contact")
    )

    recruitment_agent = models.ForeignKey(
        core_models.CompanyContact,
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
        core_models.Country,
        to_field='code2',
        null=True,
        blank=True,
        related_name="candidate_contacts"
    )

    visa_type = models.ForeignKey(
        VisaType,
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

    super_annual_fund_name = models.CharField(
        max_length=63,
        blank=True,
        verbose_name=_("Super annual Fund Name")
    )

    super_member_number = models.CharField(
        max_length=63,
        verbose_name=_("Super Member Number"),
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
        core_models.BankAccount,
        related_name="candidates",
        on_delete=models.PROTECT,
        verbose_name=_("Bank Account"),
        blank=True,
        null=True
    )

    employment_classification = models.ForeignKey(
        skill_models.EmploymentClassification,
        related_name="candidates",
        on_delete=models.PROTECT,
        verbose_name=_("Employment Classification"),
        blank=True,
        null=True
    )

    superannuation_fund = models.ForeignKey(
        SuperannuationFund,
        related_name="candidates",
        on_delete=models.PROTECT,
        verbose_name=_("Superannuation Fund"),
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
        return activity_models.Activity.objects.filter(
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
                    self.transportation_to_work is not None and
                    self.strength and self.language)
    is_personal_info_filled.short_description = _(
        'All personal info is required'
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
                    self.super_member_number and
                    self.bank_account and
                    self.emergency_contact_name and
                    self.emergency_contact_phone and
                    self.employment_classification)
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

            if current_request:
                current_user = current_request.user
                if current_user.contact.is_company_contact():
                    current_company = current_user.contact.get_closest_company()
                    company_qry = models.Q(master_company=current_company)

            candidate_rel = self.candidate_rels.get(company_qry, owner=True, active=True)
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
            from r3sourcer.apps.candidate.tasks import send_verify_sms

            send_verify_sms.apply_async(args=(self.id, workflow_object.id), countdown=10)

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

    def total_evaluation_average(self):
        cached_key = 'candidate:evaluation:avg:{}'.format(self.id)
        result = cache.get(cached_key, None)

        if result is None:
            total = 0
            counter = 0
            for evaluation in self.candidate_evaluations.all():
                if evaluation.single_evaluation_average() > 0:
                    total += evaluation.single_evaluation_average()
                    counter += 1
            result = total / counter if counter > 0 else 0
            cache.set(cached_key, result)
        return result


class TagRel(core_models.UUIDModel):
    tag = models.ForeignKey(
        core_models.Tag,
        related_name="tag_rels",
        on_delete=models.PROTECT,
        verbose_name=_("Tag")
    )

    candidate_contact = models.ForeignKey(
        CandidateContact,
        on_delete=models.PROTECT,
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
        core_models.CompanyContact,
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
        skill_models.Skill,
        related_name="candidate_skills",
        verbose_name=_("Skill")
    )

    score = models.PositiveSmallIntegerField(
        verbose_name=_("Score"),
        default=0
    )

    candidate_contact = models.ForeignKey(
        CandidateContact,
        on_delete=models.PROTECT,
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


class InterviewSchedule(core_models.UUIDModel):

    candidate_contact = models.ForeignKey(
        CandidateContact,
        on_delete=models.PROTECT,
        related_name="interview_schedules",
        verbose_name=_("Candidate Contact")
    )

    company_contact = models.ForeignKey(
        core_models.CompanyContact,
        related_name="interview_schedules",
        on_delete=models.PROTECT,
        verbose_name=_("Company Contact")
    )

    target_date_and_time = models.DateTimeField(
        verbose_name=_("Target date")
    )

    CATEGORY_CHOICES = Choices(
        ('first_phone_interview', _('First Phone Interview')),
        ('second_phone_interview', _('Second Phone Interview')),
        ('live_interview', _('Live interview')),
    )

    category = models.CharField(
        max_length=15,
        verbose_name=_("Category"),
        choices=CATEGORY_CHOICES,
        null=True,
        blank=True
    )

    accepted = models.BooleanField(
        default=False,
        verbose_name=_("Accepted")
    )

    def __str__(self):
        return "{}: {}".format(self.candidate_contact,
                               self.target_date_and_time)


class CandidateRel(core_models.UUIDModel):

    candidate_contact = models.ForeignKey(
        CandidateContact,
        on_delete=models.PROTECT,
        related_name="candidate_rels",
        verbose_name=_("Candidate Contact")
    )

    master_company = models.ForeignKey(
        core_models.Company,
        on_delete=models.CASCADE,
        related_name="candidate_rels",
        verbose_name=_("Master Company")
    )

    company_contact = models.ForeignKey(
        core_models.CompanyContact,
        related_name="candidate_rels",
        on_delete=models.PROTECT,
        verbose_name=_("Company Contact"),
        blank=True,
        null=True
    )

    owner = models.BooleanField(
        default=False,
        verbose_name=_("Is woner")
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


class AcceptanceTestRel(core_models.UUIDModel):

    acceptance_test = models.ForeignKey(
        acceptance_test_models.AcceptanceTest,
        on_delete=models.CASCADE,
        related_name='candidate_acceptance_tests',
        verbose_name=_("Acceptance Test")
    )

    candidate_contact = models.ForeignKey(
        CandidateContact,
        on_delete=models.PROTECT,
        related_name='candidate_acceptance_tests',
        verbose_name=_("Candidate Contact")
    )

    test_started_at = models.DateTimeField(
        verbose_name=_("Test Started at"),
        auto_now_add=True
    )

    test_finished_at = models.DateTimeField(
        verbose_name=_("Test Finished at"),
        auto_now=True
    )

    class Meta:
        verbose_name = _("Acceptance Test Relation")
        verbose_name_plural = _("Acceptance Test Relations")

    def __str__(self):
        return '{} {}'.format(
            str(self.candidate_contact), str(self.acceptance_test)
        )


class AcceptanceTestQuestionRel(core_models.UUIDModel):

    candidate_acceptance_test = models.ForeignKey(
        AcceptanceTestRel,
        on_delete=models.CASCADE,
        related_name='acceptance_test_question_rels',
        verbose_name=_("Acceptance Test Relation")
    )

    acceptance_test_question = models.ForeignKey(
        acceptance_test_models.AcceptanceTestQuestion,
        on_delete=models.PROTECT,
        related_name='acceptance_test_question_rels',
        verbose_name=_("Acceptance Test Question")
    )

    acceptance_test_answer = models.ForeignKey(
        acceptance_test_models.AcceptanceTestAnswer,
        on_delete=models.PROTECT,
        related_name='acceptance_test_question_rels',
        verbose_name=_("Acceptance Test Answer")
    )

    question_answered_at = models.DateTimeField(
        verbose_name=_("Question Answered at"),
        auto_now=True
    )

    class Meta:
        verbose_name = _("Acceptance Test Question Relation")
        verbose_name_plural = _("Acceptance Test Question Relations")

    def __str__(self):
        return '{}, {}: {}'.format(str(self.candidate_acceptance_test),
                                   str(self.acceptance_test_question),
                                   str(self.acceptance_test_answer))

    def get_if_correct(self):
        return self.acceptance_test_answer in \
               self.acceptance_test_question.get_correct_answers()


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

    company = models.OneToOneField(
        core_models.Company,
        on_delete=models.CASCADE,
        parent_link=True
    )

    primary_contact = models.ForeignKey(
        CandidateContact,
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
        verbose_name_plural = _("Subcontactors")

    def __str__(self):
        if (self.subcontractor_type ==
                self.SUBCONTRACTOR_TYPE_CHOICES.sole_trader):
            return str(self.primary_contact)
        return str(self.company)


class CandidateContactAnonymous(CandidateContact):

    class Meta:
        proxy = True

    def __str__(self):
        return 'Anonymous Candidate'
