import math
import os
import uuid
from datetime import date, datetime, timedelta

import collections
import re

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, Group
from django.contrib.postgres.fields import JSONField
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import APIException

from cities_light.abstract_models import (
    AbstractCity, AbstractRegion, AbstractCountry
)
from cities_light.receivers import connect_default_signals
from djmoney.models.fields import CurrencyField
from djmoney.settings import CURRENCY_CHOICES
from easy_thumbnails.fields import ThumbnailerImageField
from filer.models import Folder
from model_utils import Choices
from mptt.models import MPTTModel, TreeForeignKey
from phonenumber_field.modelfields import PhoneNumberField

from r3sourcer.apps.core.utils.user import get_default_company
from r3sourcer.apps.logger.main import endless_logger
from ..decorators import workflow_function
from ..fields import ContactLookupField
from ..managers import (
    TagManager, AbstractCompanyContactOwnerManager, AbstractObjectOwnerManager
)
from ..mixins import CompanyLookupMixin, MasterCompanyLookupMixin, CategoryFolderMixin, MYOBMixin
from ..service import factory
from ..utils.geo import fetch_geo_coord_by_address
from ..utils.validators import string_is_numeric
from ..workflow import WorkflowProcess

from .constants import MANAGER, CANDIDATE, CLIENT


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    updated_at = models.DateTimeField(verbose_name=_("Updated at"), auto_now=True, editable=False)
    created_at = models.DateTimeField(verbose_name=_("Created at"), auto_now_add=True, editable=False)

    objects = AbstractObjectOwnerManager()

    class Meta:
        abstract = True

    @classmethod
    def use_logger(cls):
        return True

    @classmethod
    def is_owned(cls):
        return True

    @property
    def object_history(self):
        return endless_logger.get_object_history(self.__class__, self.pk)


class Contact(
    CategoryFolderMixin,
    MYOBMixin,
    UUIDModel
):

    EXCLUDE_INPUT_FIELDS = (
        'files',
    )

    MARITAL_STATUS_CHOICES = Choices(
        ('Single', _('Single')),
        ('Married', _('Married')),
        ('Divorced', _('Divorced')),
        ('Widow', _('Widow')),
    )

    TITLE_CHOICES = Choices(
        ('Mr.', _('Mr.')),
        ('Ms.', _('Ms.')),
        ('Mrs.', _('Mrs.')),
        ('Dr.', _('Dr.')),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name='contact',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    title = models.CharField(
        max_length=7,
        verbose_name=_("Title"),
        choices=TITLE_CHOICES,
        blank=True,
        null=True,
    )

    first_name = models.CharField(
        max_length=255,
        verbose_name=_("First Name"),
        blank=True
    )

    last_name = models.CharField(
        max_length=255,
        verbose_name=_("Last Name"),
        blank=True
    )

    email = models.EmailField(
        max_length=255,
        verbose_name=_("E-mail"),
        null=True,
        blank=True,
        unique=True,
    )

    phone_mobile = PhoneNumberField(
        verbose_name=_("Mobile Phone"),
        null=True,
        blank=True,
        unique=True,
    )

    gender = models.CharField(
        max_length=7,
        verbose_name=_("Gender"),
        null=True,
        blank=True,
        choices=(("male", _("Male")), ("female", _("Female")))
    )

    marital_status = models.CharField(
        max_length=15,
        verbose_name=_("Marital Status"),
        choices=MARITAL_STATUS_CHOICES,
        null=True,
        blank=True
    )

    birthday = models.DateField(verbose_name=_("Birthday"), blank=True, null=True)
    spouse_name = models.CharField(max_length=63, blank=True, verbose_name=_("Spouse/Partner name"))
    children = models.PositiveSmallIntegerField(verbose_name=_("Children"), blank=True, null=True)

    is_available = models.BooleanField(verbose_name=_("Available"), default=True)

    picture = ThumbnailerImageField(
        upload_to='contact_pictures',
        default=os.path.join('contact_pictures', 'default_picture.jpg'),
        max_length=255,
        blank=True
    )

    phone_mobile_verified = models.BooleanField(verbose_name=_("Mobile Phone Verified"), default=False)
    email_verified = models.BooleanField(verbose_name=_("E-mail Verified"), default=False)

    address = models.ForeignKey(
        'Address',
        verbose_name=_("Address"),
        related_name='contacts',
        null=True
    )

    files = models.ForeignKey(
        Folder,
        related_name='contacts',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")
        unique_together = ('first_name', 'last_name', 'email', 'phone_mobile')

    def __str__(self):
        name = '{} {}'.format(self.first_name, self.last_name)
        if self.title:
            name = '{} {}'.format(self.title, name)
        return name

    @property
    def notes(self):
        return Note.objects.filter(
            content_type__model=self.__class__.__name__,
            object_id=self.pk
        )

    def get_availability(self):
        unavailable = self.contact_unavailabilities.filter(
            unavailable_from__lte=date.today(),
            unavailable_until__gte=date.today()
        )
        if len(unavailable) > 0:
            return False
        return self.is_available
    get_availability.boolean = True

    def is_company_contact(self):
        return self.company_contact.exists()
    is_company_contact.boolean = True

    def is_candidate_contact(self):
        return hasattr(self, 'candidate_contacts')

    def get_job_title(self):
        if self.company_contact.exists():
            for company_contact in self.company_contact.all():
                if company_contact.relationships.filter(company__type=Company.COMPANY_TYPES.master).exists():
                    return company_contact.job_title
            return self.company_contact.first().job_title

    def get_company_contact_by_company(self, company):
        if self.is_company_contact():
            for company_contact in self.company_contact.all():
                if company_contact.relationships.filter(company=company).exists():
                    return company_contact
        return None

    def is_master_related(self):
        if self.company_contact.exists():
            for company_contact in self.company_contact.all():
                if company_contact.relationships.filter(company__type=Company.COMPANY_TYPES.master).exists():
                    return True
        return False

    def get_role(self):
        if self.is_company_contact():
            return self.company_contact.first().role
        elif self.is_candidate_contact():
            return CANDIDATE
        return None

    def get_role_id(self):
        if self.is_company_contact():
            return self.company_contact.first().id
        elif self.is_candidate_contact():
            return self.candidate_contacts.id
        return None

    def get_closest_company(self):
        from r3sourcer.apps.core.utils.companies import get_site_master_company

        if self.is_company_contact():
            master_company = self.company_contact.first().get_master_company()
            if len(master_company) > 0:
                return master_company[0]
        elif self.is_candidate_contact():
            return self.candidate_contacts.get_closest_company()

        return get_site_master_company() or get_default_company()

    def process_sms_reply(self, sent_sms, reply_sms, positive):
        if positive:
            self.phone_mobile_verified = True
            self.save(update_fields=['phone_mobile_verified'])

    def save(self, *args, **kwargs):
        is_adding = self._state.adding
        if not self.email and not self.phone_mobile:
            raise ValidationError(_('Contact must have email and/or mobile phone number.'))

        if is_adding and self.user is None:
            user = User.objects.create(email=self.email, phone_mobile=self.phone_mobile)
            self.user = user

        super().save(*args, **kwargs)


class ContactUnavailability(UUIDModel):

    contact = models.ForeignKey(
        Contact,
        related_name="contact_unavailabilities",
        verbose_name=_("Contact"),
        on_delete=models.CASCADE
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
        verbose_name = _("Contact Unavailability")
        verbose_name_plural = _("Contact Unavailabilities")

    def __str__(self):
        return '{} {} - {}'.format(str(self.contact), self.unavailable_from, self.unavailable_until)


class UserManager(BaseUserManager):

    use_in_migrations = True

    def _create_user(self, password, **extra_fields):
        """
        Creates and saves a User and Contact
        """
        email = self.normalize_email(extra_fields.pop('email', '')) or None
        phone_mobile = extra_fields.pop('phone_mobile', None)
        if not email and not phone_mobile:
            raise ValueError('User must have email and/or mobile phone number.')

        obj = self.model(email=email, phone_mobile=phone_mobile, **extra_fields)
        obj.set_password(password)
        obj.save()

        # Lookup fields create contact object implicitly
        # in ContactLookupField.__get__
        obj.contact.save()
        return obj

    def create_user(self, password=None, **extra_fields):
        extra_fields['is_staff'] = False
        extra_fields['is_superuser'] = False

        return self._create_user(password, **extra_fields)

    def create_superuser(self, password, **extra_fields):
        extra_fields['is_staff'] = True
        extra_fields['is_superuser'] = True

        return self._create_user(password, **extra_fields)


class User(UUIDModel,
           AbstractBaseUser,
           PermissionsMixin):

    EXCLUDE_INPUT_FIELDS = (
        'last_login', 'date_joined', 'is_staff', 'is_superuser', 'is_active',
        'is_superuser', 'groups', 'permissions', 'password'
    )

    email = ContactLookupField(lookup_model=Contact)
    phone_mobile = ContactLookupField(lookup_model=Contact)
    username = ContactLookupField(lookup_model=Contact,
                                  lookup_name='email',
                                  read_only=True)

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    role = models.ManyToManyField('Role')

    USERNAME_FIELD = 'id'
    REQUIRED_FIELDS = ['email', 'phone_mobile']

    objects = UserManager()

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return str(self.contact)

    def get_short_name(self):
        return str(self)

    def first_name(self):
        return self.contact.first_name

    def last_name(self):
        return self.contact.last_name

    def get_full_name(self):
        return '{} {}'.format(self.first_name(), self.last_name())
    get_full_name.short_description = _("Full name")

    def clean(self):
        if self.is_superuser \
                and User.objects.filter(is_superuser=True).exists() \
                and not User.objects.filter(is_superuser=True, id=self.id).exists():
            contact = getattr(self, "contact")
            relation = CompanyContactRelationship.objects.filter(
                company=get_default_company(),
                company_contact__contact=contact
            ).exists()

            if contact and not relation:
                raise ValidationError(
                    _("Additional superuser could be created only for "
                      "contact employed to SYSTEM_MASTER_COMPANY"))
            else:
                self.is_superuser = False

    def is_candidate(self) -> bool:
        return hasattr(self.contact, 'candidate_contacts')

    def is_manager(self) -> bool:
        if self.contact.company_contact.first():
            return self.contact.company_contact.first().role == MANAGER
        return False

    def is_client(self) -> bool:
        if self.contact.company_contact.first():
            return self.contact.company_contact.first().role == CLIENT
        return False

    @property
    def access_level(self) -> str:
        if self.is_manager():
            return MANAGER
        elif self.is_client():
            return CLIENT
        elif self.is_candidate():
            return CANDIDATE
        raise ValidationError("Unknown user role")

    def has_permission(self, permission_codename) -> bool:
        from r3sourcer.apps.company_settings.models import GlobalPermission

        try:
            permission = GlobalPermission.objects.get(codename=permission_codename)
            return permission in self.user_permissions.all()
        except GlobalPermission.DoesNotExist:
            return False

    def has_group_permission(self, permission_codename) -> bool:
        from r3sourcer.apps.company_settings.models import GlobalPermission

        try:
            groups = self.groups.all()
            granted_permissions = GlobalPermission.objects.filter(group__in=groups)
            permission = GlobalPermission.objects.get(codename=permission_codename)
            return permission in granted_permissions
        except GlobalPermission.DoesNotExist:
            return False

    @property
    def company(self):
        try:
            if self.is_client() or self.is_manager():
                return self.contact.company_contact.first().relationships.first().company
            elif self.is_candidate():
                return self.contact.candidate_contacts.candidate_rels.first().master_company
            else:
                raise APIException("Unknown user's role.")
        except AttributeError:
            return None

    @property
    def company_files(self):
        company_file_tokens = self.company.company_file_tokens.all()
        return [x.company_file for x in company_file_tokens]


class Country(UUIDModel, AbstractCountry):
    currency = CurrencyField(default='USD', choices=CURRENCY_CHOICES)

    class Meta:
        verbose_name = _("Country")
        verbose_name_plural = _("Countries")

    @classmethod
    def is_owned(cls):
        return False


class Region(UUIDModel,
             AbstractRegion):

    class Meta:
        verbose_name = _("State/District")
        verbose_name_plural = _("States/Districts")

    @classmethod
    def is_owned(cls):
        return False

    @classmethod
    def get_countrys_regions(cls, country_code):
        regions = cls.objects.filter(country__code2=country_code).distinct().values('id', 'name')
        return [{'label': r['name'], 'value': r['id']} for r in regions]

    def __str__(self):
        return self.name


class City(UUIDModel,
           AbstractCity):

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")

    @classmethod
    def is_owned(cls):
        return False

    def __str__(self):
        return self.name


class Address(UUIDModel):

    default_errors = {
        'fetch_error': _("Can't get coordinates by address")
    }

    street_address = models.CharField(
        max_length=126,
        verbose_name=_("Street Address")
    )

    city = models.ForeignKey(City, null=True, blank=True)

    postal_code = models.CharField(max_length=11, blank=True, verbose_name=_("Postal Code"))

    state = models.ForeignKey(Region, blank=True, null=True, verbose_name=_("State/District"))

    latitude = models.DecimalField(max_digits=18, decimal_places=15, default=0)
    longitude = models.DecimalField(max_digits=18, decimal_places=15, default=0)

    country = models.ForeignKey(Country, to_field='code2', default='AU')

    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")

    def __str__(self):
        address = '{}\n{}'.format(self.street_address, self.postal_code)
        if self.city:
            country_part = ' {}\n{}'.format(self.city.name,
                                            self.country.name)
        else:
            country_part = '\n{}'.format(self.country.name)

        return '{}{}'.format(address, country_part)

    def get_full_address(self):
        if self.city:
            city_part = ',\n{} {}'.format(self.city.name, self.postal_code)
        else:
            city_part = ',\n{}'.format(self.postal_code)

        if self.state:
            country_part = ' {},\n{}'.format(self.state.name,
                                             self.country.name)
        else:
            country_part = ',\n{}'.format(self.country.name)

        return '{}{}{}'.format(self.street_address, city_part, country_part)

    def get_city_address(self):
        if self.city:
            city_part = '{} {}'.format(self.city.name, self.postal_code)
        else:
            city_part = '{}'.format(self.postal_code)

        if self.state:
            country_part = ' {} {}'.format(self.state.name,
                                           self.country.name)
        else:
            country_part = ' {}'.format(self.country.name)

        return '{}{}'.format(city_part, country_part)

    def get_address(self):
        if self.city:
            city_part = '{}, {},'.format(self.street_address, self.city.name)
        else:
            city_part = '{},'.format(self.street_address)

        address = '{} {}'.format(city_part, self.postal_code)
        if self.state:
            address = '{} {}'.format(address, self.state.name)
        return address

    def fetch_geo_coord(self, should_save=True):
        if self.latitude and self.longitude:
            return False

        latitude, longitude = fetch_geo_coord_by_address(self.get_full_address())
        if latitude and longitude:
            self.latitude = latitude
            self.longitude = longitude
            if should_save:
                self.save(update_fields=['latitude', 'longitude'])
            return True
        return False

    def save(self, *args, **kwargs):
        if self._state.adding:
            bind_address = True
        else:
            original = type(self).objects.get(id=self.id)
            bind_address = original.get_full_address() != self.get_full_address()
        if bind_address and not self.fetch_geo_coord(False):
            if getattr(settings, 'FETCH_ADDRESS_RAISE_EXCEPTIONS', True):
                raise ValidationError(self.default_errors['fetch_error'])
        super(Address, self).save(*args, **kwargs)


class CompanyContact(UUIDModel, MasterCompanyLookupMixin):
    MANAGER = 'manager'
    CLIENT = 'client'
    ROLE_CHOICES = Choices(
        (MANAGER, _('Manager')),
        (CLIENT, _('Client')),
    )

    contact = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        related_name="company_contact",
        verbose_name=_("Contact")
    )

    job_title = models.CharField(max_length=31, blank=True, verbose_name=_("Job title"))

    rating_unreliable = models.BooleanField(
        verbose_name=_("Ratings Unreliable"),
        help_text=_("Mark when rates Candidates badly but wants them again on the jobsite"),
        default=False
    )

    receive_job_confirmation_sms = models.BooleanField(
        verbose_name=_("Receive Job confirmation sms"),
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

    legacy_myob_card_number = models.CharField(
        max_length=15,
        verbose_name=_("Legacy MYOB card number"),
        blank=True
    )

    approved_by_primary_contact = models.ForeignKey(
        'Contact',
        verbose_name=_("Approved by primary contact"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False,
        related_name="primary_approvals",
    )

    primary_contact_approved_at = models.DateTimeField(
        verbose_name=_("Primary Contact approved at"),
        null=True,
        editable=False
    )

    approved_by_staff = models.ForeignKey(
        'Contact',
        verbose_name=_("Approved by staff"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False,
        related_name="staff_approvals",
    )

    staff_approved_at = models.DateTimeField(verbose_name=_("Staff approved at"), null=True, editable=False)

    pin_code = models.CharField(
        verbose_name=_("PIN"),
        validators=[string_is_numeric, MinLengthValidator(4)],
        max_length=16,
        blank=True,
        default=''
    )

    role = models.CharField(max_length=63, choices=ROLE_CHOICES, default=ROLE_CHOICES.manager, verbose_name=_('Role'))

    timesheet_reminder = models.BooleanField(
        verbose_name=_("Timesheet Reminder"),
        help_text=_("Unmark when Company Contact does not need timesheet sign reminders"),
        default=True
    )

    objects = AbstractCompanyContactOwnerManager()

    class Meta:
        verbose_name = _("Company Contact")
        verbose_name_plural = _("Company Contacts")

    def __str__(self):
        return '{} {}'.format(self.job_title, str(self.contact))

    def get_master_company(self):
        master_companies = []
        for rel in self.relationships.all():
            master_companies.extend(rel.get_master_company())
        return master_companies

    @classmethod
    def get_master_company_lookup(cls, master_company):
        return Q(relationships__company=master_company)


class BankAccount(UUIDModel):
    bank_name = models.CharField(max_length=63, verbose_name=_("Bank Name"))
    bank_account_name = models.CharField(max_length=63, verbose_name=_("Bank Account Name"))
    bsb = models.CharField(max_length=6, verbose_name=_("BSB"))
    account_number = models.CharField(max_length=10, verbose_name=_("Account Number"))

    contact = models.ForeignKey(
        Contact,
        related_name="bank_accounts",
        on_delete=models.PROTECT,
        verbose_name="Contact"
    )

    class Meta:
        verbose_name = _("Bank Account")
        verbose_name_plural = _("Bank Accounts")

    def __str__(self):
        return '{}: {}'.format(self.bank_name, self.bank_account_name)


class Company(
    CategoryFolderMixin,
    MYOBMixin,
    UUIDModel,
    MasterCompanyLookupMixin
):

    name = models.CharField(max_length=127, verbose_name=_("Company Name"), unique=True)

    short_name = models.CharField(
        max_length=63,
        help_text=_('Used for Jobsite naming'),
        verbose_name=_("Short name"),
        null=True,
        blank=True,
        unique=True,
    )

    business_id = models.CharField(
        max_length=31,
        verbose_name=_("Business Number"),
        null=True,
        blank=True,
    )

    registered_for_gst = models.BooleanField(
        verbose_name=_("Registered for GST"),
        default=False
    )

    tax_number = models.CharField(
        max_length=31,
        verbose_name=_("Tax Number"),
        null=True,
        blank=True
    )

    website = models.URLField(verbose_name=_("Website"), blank=True)

    logo = ThumbnailerImageField(
        upload_to='company_pictures',
        default=os.path.join('company_pictures', 'default_picture.jpg'),
        blank=True
    )

    date_of_incorporation = models.DateField(
        verbose_name=_("Date of Incorporation"),
        null=True,
        blank=True
    )

    description = models.TextField(
        verbose_name=_("Public description"),
        blank=True
    )

    notes = models.TextField(
        verbose_name=_("Notes"),
        blank=True,
        help_text=_("Visible for anyone with access")
    )

    manager = models.ForeignKey(
        CompanyContact,
        on_delete=models.PROTECT,
        related_name="companies",
        verbose_name=_("Manager"),
        null=True, blank=True,
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent Company")
    )

    industry = models.ForeignKey(
        'pricing.Industry',
        on_delete=models.PROTECT,
        related_name="companies",
        verbose_name=_("Industry"),
        null=True,
        blank=True,
    )

    CREDIT_CHECK_CHOICES = Choices(
        (True, 'approved', _("Approved")),
        (False, 'not_approved', _("Not Approved")),
    )

    credit_check = models.BooleanField(
        verbose_name=_("Credit Check"),
        choices=CREDIT_CHECK_CHOICES,
        default=CREDIT_CHECK_CHOICES.not_approved
    )

    credit_check_date = models.DateField(
        verbose_name=_("Credit Check Approval Date"),
        null=True,
        blank=True
    )

    approved_credit_limit = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Approved Credit Limit")
    )

    TERMS_PAYMENT_CHOICES = Choices(
        ('prepaid', _('Prepaid')),
        ('on_delivery', _('Cash on delivery')),
        ('days', _('Days')),
        ('day_of_month', _('Day of the month')),
        ('days_eom', _('Days after EOM')),
        ('day_of_month_eom', _('Day of month after EOM')),
    )

    terms_of_payment = models.CharField(
        verbose_name=_("Terms of Payment"),
        choices=TERMS_PAYMENT_CHOICES,
        default=TERMS_PAYMENT_CHOICES.on_delivery,
        max_length=20
    )

    payment_due_date = models.PositiveSmallIntegerField(
        verbose_name=_("Number of days to pay"),
        help_text=_("Or set the day of the month within which the payment must be made to pay"),
        default=0
    )

    available = models.BooleanField(verbose_name=_("Available"), default=True)

    billing_email = models.EmailField(
        max_length=255,
        verbose_name=_("Billing E-mail"),
        blank=True,
        null=True
    )

    def clients_credit_path(instance, filename):
        return 'clients/credit_checks/{}/{}'.format(instance.id, filename)

    credit_check_proof = models.FileField(
        verbose_name=_("Credit Check Proof"), upload_to=clients_credit_path, null=True, blank=True)

    bank_account = models.ForeignKey(
        BankAccount,
        related_name="companies",
        on_delete=models.PROTECT,
        verbose_name=_("Bank Account"),
        null=True,
        blank=True
    )

    COMPANY_TYPES = Choices(
        ('master', _('Master')),
        ('regular', _('Regular'))
    )

    type = models.CharField(
        verbose_name=_("Company type"),
        choices=COMPANY_TYPES,
        default=COMPANY_TYPES.regular,
        max_length=20
    )

    COMPANY_RATING = Choices(
        ('aa', _('AA')),
        ('ab', _('AB')),
        ('ba', _('BA')),
        ('bb', _('BB'))
    )

    company_rating = models.CharField(
        verbose_name=_("Company rating"),
        choices=COMPANY_RATING,
        default=COMPANY_RATING.aa,
        max_length=2
    )

    files = models.ForeignKey(
        Folder,
        related_name='companies',
        null=True,
        blank=True,
    )

    TIMESHEET_APPROVAL_SCHEME = Choices(
        ('PIN', _("PIN")),
        ('SIGNATURE', _("Signature"))
    )

    timesheet_approval_scheme = models.CharField(
        verbose_name=_("TimeSheet approval scheme"),
        default=TIMESHEET_APPROVAL_SCHEME.PIN,
        choices=TIMESHEET_APPROVAL_SCHEME,
        max_length=16
    )

    expense_account = models.CharField(
        max_length=6,
        verbose_name=_('MYOB Expense Account'),
        default='4-1000',
    )

    is_system = models.BooleanField(
        default=False,
        editable=False,
        verbose_name=_('System Company')
    )

    groups = models.ManyToManyField(Group, related_name='companies')

    stripe_customer = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = _("Company")
        verbose_name_plural = _("Companies")

    def __str__(self):
        return self.name

    def get_formatted_abn(self):
        abn = self.business_id
        if self.business_id and len(self.business_id) == 11:
            abn = '{}{} {}{}{} {}{}{} {}{}{}'.format(*self.business_id)

        return abn

    def is_manager_assigned(self):
        return self.manager is not None
    is_manager_assigned.short_description = _("Bind manager")

    def get_hq_address(self):
        if self.company_addresses.filter(hq=True).exists():
            return self.company_addresses.filter(hq=True).first()
        return None

    def is_business_id_set(self):
        return bool(self.business_id)
    is_business_id_set.short_description = _("Business id didn't set")

    def get_contact(self):
        return self.manager.contact if self.manager else None

    def get_user(self):
        contact = self.get_contact()
        return contact.user if contact else None

    def get_master_company(self):
        if self.type == self.COMPANY_TYPES.master:
            return [self]
        else:
            master_companies = []
            for company_rel in self.regular_companies.all():
                master_companies.extend(company_rel.master_company.get_master_company())
            return master_companies

    @classmethod
    def get_master_company_lookup(cls, master_company):
        return Q(id=master_company.id)

    def get_regular_companies(self):
        if self.type == self.COMPANY_TYPES.regular:
            return [self]
        reg_companies = []
        for company_rel in self.master_companies.all():
            reg_companies.extend(company_rel.regular_company.get_regular_companies())
        return reg_companies

    def get_terms_of_payment(self):
        if self.terms_of_payment in (self.TERMS_PAYMENT_CHOICES.prepaid,
                                     self.TERMS_PAYMENT_CHOICES.on_delivery):
            return self.TERMS_PAYMENT_CHOICES[self.terms_of_payment]
        return '{}: {}'.format(
            self.TERMS_PAYMENT_CHOICES[self.terms_of_payment],
            self.payment_due_date
        )

    def get_effective_pricelist_qs(self, position=None):
        qs = self.price_lists.exclude(
            Q(approved_by__isnull=True) | Q(approved_by=None) | Q(approved_at__isnull=True) | Q(approved_at=None)
        ).filter(
            effective=True,
            valid_until__gte=date.today(),
            price_list_rates__skill__active=True,
            price_list_rates__hourly_rate__gt=0
        )

        if position:
            qs = qs.filter(price_list_rates__skill=position)

        return qs

    def get_portfolio_manager(self):
        company_rel = self.regular_companies.all().first()
        return company_rel and company_rel.primary_contact

    @property
    def invoice_rule(self):
        return self.invoice_rules.first()

    @property
    def is_master(self):
        return self.type == self.COMPANY_TYPES.master

    @property
    def currency(self):
        try:
            return self.company_addresses.order_by('hq').first().address.country.currency.lower()
        except Exception:
            return 'aud'

    @property
    def active_subscription(self):
        return self.subscriptions.filter(active=True).first()

    def active_workers(self, start_date=None):
        from r3sourcer.apps.candidate.models import CandidateContact

        if not start_date:
            start_date = datetime.today() - timedelta(days=31)

        return CandidateContact.objects.filter(job_offers__time_sheets__shift_started_at__gt=start_date).count()

    def save(self, *args, **kwargs):
        from r3sourcer.apps.company_settings.models import CompanySettings, MYOBSettings
        from r3sourcer.apps.hr.models import PayslipRule

        super(Company, self).save(*args, **kwargs)

        if not hasattr(self, 'company_settings'):
            CompanySettings.objects.create(company=self)

        if not hasattr(self, 'myob_settings'):
            MYOBSettings.objects.create(company=self)

        if not self.payslip_rules.all():
            PayslipRule.objects.create(company=self)

        if not self.invoice_rules.all():
            InvoiceRule.objects.create(company=self)


class CompanyRel(
        UUIDModel,
        WorkflowProcess,
        CompanyLookupMixin,
        MasterCompanyLookupMixin):
    """
    Model for storing master and regular company relationship
    """
    master_company = models.ForeignKey(
        Company,
        related_name="master_companies",
        verbose_name=_("Master company"),
        on_delete=models.PROTECT
    )

    regular_company = models.ForeignKey(
        Company,
        related_name="regular_companies",
        verbose_name=_("Regular company"),
        on_delete=models.CASCADE
    )

    primary_contact = models.ForeignKey(
        CompanyContact,
        related_name="company_accounts",
        verbose_name=_("Primary Contact"),
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ('master_company', 'regular_company')
        verbose_name = _("Company Relationship")
        verbose_name_plural = _("Company Relationships")

    def __str__(self):
        return "{}/{}".format(self.master_company, self.regular_company)

    @workflow_function
    def is_primary_contact_identified(self):
        return self.primary_contact is not None
    is_primary_contact_identified.short_description = _("Identify portfolio manager")

    @workflow_function
    def is_manager_assigned(self):
        return self.regular_company.is_manager_assigned()
    is_manager_assigned.short_description = _("Identify primary Contact")

    @workflow_function
    def is_business_id_set(self):
        return self.regular_company.is_business_id_set()

    @workflow_function
    def is_state_60_available(self):
        req_class = factory.get_instance('company_state_60')
        return req_class.check(self)

    @workflow_function
    def is_address_valid(self):
        return self.regular_company.company_addresses.filter(active=True).exists()
    is_address_valid.short_description = _("Active address")

    @workflow_function
    def is_description_set(self):
        return bool(self.regular_company.description)
    is_description_set.short_description = _("Public description")

    @workflow_function
    def is_industry_set(self):
        return bool(self.regular_company.industry)
    is_industry_set.short_description = _("Industry")

    def get_master_company(self):
        return self.master_company.get_master_company()

    def get_closest_company(self):
        return self.master_company

    def after_state_created(self, workflow_object):
        if workflow_object.state.number == 70 and workflow_object.active:
            jobs = self._get_jobs_with_states(40)

            for job in jobs:
                if job.is_allowed(20):
                    job.create_state(20)
        elif workflow_object.state.number == 80 and workflow_object.active:
            jobs = self._get_jobs_with_states(20)

            for job in jobs:
                if job.is_allowed(40):
                    job.create_state(40)

    def _get_jobs_with_states(self, state):
        from r3sourcer.apps.hr.models import Job

        content_type = ContentType.objects.get_for_model(Job)
        filter_values = WorkflowObject.objects.filter(
            state__number=state, state__workflow__model=content_type, active=True
        ).values_list('object_id', flat=True).distinct()

        return self.regular_company.customer_jobs.filter(id__in=filter_values)

    def save(self, *args, **kwargs):
        just_added = self._state.adding
        super().save(*args, **kwargs)

        if just_added:
            self.create_state(10)

        cache.set('company_rel_{}'.format(self.regular_company.id), None)


class CompanyContactRelationship(
        UUIDModel,
        CompanyLookupMixin,
        MasterCompanyLookupMixin):
    company = models.ForeignKey(
        Company,
        related_name="relationships",
        verbose_name=_("Company"),
        on_delete=models.PROTECT
    )

    company_contact = models.ForeignKey(
        CompanyContact,
        related_name="relationships",
        verbose_name=_("Company Contact"),
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    active = models.BooleanField(verbose_name=_("Active"), default=True)
    termination_date = models.DateField(
        verbose_name=_("Termination date"),
        null=True,
        blank=True
    )

    def __str__(self):
        return "{company}: {contact}".format(company=self.company, contact=self.company_contact)

    def get_master_company(self):
        return self.company.get_master_company()

    def get_closest_company(self):
        if self.termination_date and self.termination_date < timezone.now():
            return None
        return self.company

    @classmethod
    def get_master_company_lookup(cls, master_company):
        return Q(company=master_company)

    def save(self, *args, **kwargs):
        is_added = self._state.adding
        super().save(*args, **kwargs)

        if is_added:
            role = Role.ROLE_NAMES.client
            if self.company.type == self.company.COMPANY_TYPES.master:
                role = Role.ROLE_NAMES.manager

            self.company_contact.contact.user.role.add(Role.objects.create(name=role))


class CompanyAddress(
        UUIDModel,
        MasterCompanyLookupMixin):

    name = models.CharField(
        max_length=63,
        blank=True,
        verbose_name=_("Name")
    )

    company = models.ForeignKey(
        Company,
        related_name='company_addresses',
        on_delete=models.CASCADE,
        verbose_name=_("Company"),
    )

    address = models.ForeignKey(
        Address,
        related_name='company_addresses',
        on_delete=models.PROTECT,
        verbose_name=_("Address"),
    )

    hq = models.BooleanField(default=False, verbose_name=_("HQ"))

    termination_date = models.DateField(
        verbose_name=_("Termination date"),
        null=True,
        blank=True
    )

    primary_contact = models.ForeignKey(
        CompanyContact,
        related_name='company_primary_addresses',
        verbose_name=_("Primary contact"),
        null=True,
        blank=True
    )

    active = models.BooleanField(default=True, verbose_name=_("Active"))

    phone_landline = PhoneNumberField(blank=True, verbose_name=_("Landline Phone"))
    phone_fax = PhoneNumberField(blank=True, verbose_name=_("Fax"))

    class Meta:
        verbose_name = _("Company Address")
        verbose_name_plural = _("Company Addresses")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.hq:
            CompanyAddress.objects.filter(company=self.company).update(hq=False)
        elif not CompanyAddress.objects.filter(company=self.company, hq=True).exists():
            self.hq = True

        super(CompanyAddress, self).save(*args, **kwargs)

    def get_master_company(self):
        return self.company.get_master_company()

    @classmethod
    def get_master_company_lookup(cls, master_company):
        return Q(company=master_company)


class CompanyContactAddress(
        UUIDModel,
        MasterCompanyLookupMixin):

    company_address = models.ForeignKey(
        CompanyAddress,
        related_name="company_contacts",
        verbose_name=_("Company Address"),
        on_delete=models.PROTECT
    )

    company_contact = models.ForeignKey(
        CompanyContact,
        related_name="company_addresses",
        verbose_name=_("Company Contact"),
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    active = models.BooleanField(verbose_name=_("Active"), default=True)
    termination_date = models.DateField(
        verbose_name=_("Termination date"),
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _("Company Contact Address")
        verbose_name_plural = _("Company Contact Addresses")

    def __str__(self):
        return '{} {}'.format(str(self.company_contact),
                              str(self.company_address))

    @classmethod
    def get_master_company_lookup(cls, master_company):
        return Q(company_contact__relationships__company=master_company)

    def get_master_company(self):
        return self.company_contact.get_master_company()


class FileStorage(UUIDModel):
    PATHS = Choices(
        (('core', 'contact'), 'contacts/{owner.id}/{filename}'),
        (('core', 'company'), 'companies/{owner.id}/{filename}'),
    )
    owner_type = models.ForeignKey(
        ContentType,
        limit_choices_to=Q(app_label='core', model__in=['contact', 'company']),
        on_delete=models.CASCADE
    )
    owner_id = models.UUIDField()
    owner = GenericForeignKey('owner_type', 'owner_id')

    def content_path(self, filename):
        if self.owner is None:
            raise NotImplementedError('owner must be assigned before content can be used')

        natural_key = self.owner_type.natural_key()
        try:
            pattern = self.PATHS[natural_key]
            return pattern.format(
                filename=filename,
                owner=self.owner,
                instance=self,
            )
        except KeyError:
            raise NotImplementedError('content_path not support {} model'.format('.'.join(natural_key)))

    content = models.FileField(
        upload_to=content_path,
        verbose_name=_("Content"),
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _("File Storage")
        verbose_name_plural = _("File Storage")

    @classmethod
    def is_owned(cls):
        return False


class CompanyLocalization(UUIDModel):
    field_name = models.CharField(
        max_length=64,
        verbose_name=_("Company field name"),
    )
    country = models.ForeignKey(
        Country,
        to_field='code2',
        null=True,
        blank=True,
        help_text=_("Country of localization. Empty value used for default variant")
    )
    verbose_value = models.CharField(
        max_length=128,
        verbose_name=_("Company field verbose name"),
        null=True,
        blank=True,
    )
    help_text = models.CharField(
        max_length=512,
        verbose_name=_("Company field help text"),
        null=True,
        blank=True,
    )
    active = models.BooleanField(
        verbose_name=_("Company field is active"),
        default=True,
    )

    class Meta:
        verbose_name = _("Company Localization")
        verbose_name_plural = _("Company Localizations")

    @classmethod
    def get_company_metadata(cls, country=None):
        """
        Obtain company localization metadata in format::

            {
                "business_id": {
                    "verbose_value": "<verbose_value>",
                    "help_text": "<help_text>",
                    "active": bool,
                },
                "tax_number": {
                    "verbose_value": "<verbose_value>",
                    "help_text": "<help_text>",
                    "active": bool,
                }
            }

        Metadata picked for business_id and tax_number fields for given country or default variant.
        Company localization with empty country used as default variant

        :param country: Country to make lookup
        :return: Dict with metadata
        """
        localizations = cls.objects.filter(
            Q(country__in=[country]) | Q(country__isnull=True),
            field_name__in=["business_id", "tax_number"]
        )
        lookup = dict()
        for company in localizations:
            field_name = company.field_name
            if field_name in lookup and company.country is None:
                continue

            lookup[field_name] = dict(
                verbose_value=company.verbose_value,
                help_text=company.help_text,
                active=company.active,
            )
        return lookup


class CompanyTradeReference(UUIDModel):

    trade_reference = models.TextField(verbose_name=_("Trade Reference"))

    company = models.ForeignKey(
        Company,
        related_name="company_trade_references",
        on_delete=models.CASCADE,
        verbose_name=_("Company")
    )

    referral_company_name = models.CharField(
        max_length=255,
        verbose_name=_("Company Name")
    )

    referral_person_name = models.CharField(
        max_length=255,
        verbose_name=_("Title, First and Last Name")
    )

    referral_email = models.EmailField(verbose_name=_("E-mail"))
    referral_phone = PhoneNumberField(verbose_name=_("Phone"))

    email_auth_code = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("E-mail authentication string")
    )

    class Meta:
        verbose_name = _("Company Trade Reference")
        verbose_name_plural = _("Company Trade References")

    def __str__(self):
        return _('{} from {}').format(self.company.name, self.referral_company_name)


class Note(UUIDModel):

    content_type = models.ForeignKey(
        ContentType,
        verbose_name=_("Content type")
    )
    object_id = models.UUIDField(verbose_name=_("Object id"))
    object = GenericForeignKey()

    note = models.TextField(
        verbose_name=_("Notes"),
        blank=True
    )

    def __str__(self):
        return '{} {}'.format(str(self.content_type), _("Note"))

    class Meta:
        verbose_name = _("Contact Note")
        verbose_name_plural = _("Contact Notes")

    @classmethod
    def is_owned(cls):
        return False


class Tag(MPTTModel, UUIDModel):
    name = models.CharField(max_length=63, verbose_name=_("Tag Name"))
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True)
    active = models.BooleanField(default=True, verbose_name=_('Active'))
    evidence_required_for_approval = models.BooleanField(
        default=False,
        verbose_name=_('Evidence required for approval')
    )
    # __original_active = None

    objects = TagManager()

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")

    # def __init__(self, *args, **kwargs):
    #     super(Tag, self).__init__(*args, **kwargs)
    #     self.__original_active = self.active
    #
    # def save(self, *args, **kwargs):
    #     if self.__original_active != self.active:
    #         self.candidate_tags.update(verified_by=None)
    #     super(Tag, self).save(*args, **kwargs)
    #     self.__original_active = self.active

    def __str__(self):
        return self.name


class VAT(UUIDModel):
    country = models.ForeignKey(Country, to_field='code2', default='AU')
    name = models.CharField(
        max_length=64,
        verbose_name=_("Name"),
    )
    rate = models.DecimalField(
        decimal_places=2,
        max_digits=16,
        verbose_name=_("Rate"),
        default=0.00
    )
    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(verbose_name=_("End Date"), blank=True, null=True)

    class Meta:
        verbose_name = _("VAT")
        verbose_name_plural = _("VATs")

    @classmethod
    def is_owned(cls):
        return False


class AbstractBaseOrder(
        UUIDModel,
        WorkflowProcess,
        CompanyLookupMixin,
        MasterCompanyLookupMixin):

    provider_company = models.ForeignKey(  # master
        Company,
        on_delete=models.PROTECT,
        verbose_name=_("Provider Company"),
        related_name="provider_%(class)ss",
    )

    customer_company = models.ForeignKey(  # any company
        Company,
        on_delete=models.CASCADE,
        verbose_name=_("Customer Company"),
        related_name="customer_%(class)ss",
    )

    provider_representative = models.ForeignKey(
        CompanyContact,
        on_delete=models.PROTECT,
        verbose_name=_("Provider Representative"),
        related_name="provider_representative_%(class)ss",
        blank=True,
        null=True
    )

    customer_representative = models.ForeignKey(
        CompanyContact,
        on_delete=models.PROTECT,
        verbose_name=_("Customer Representative"),
        related_name="customer_representative_%(class)ss",
        null=True,
        blank=True,
    )

    # TODO: change path to files
    def customer_signature_path(self, filename):
        pattern = '{year}/{owner.id}/{filename}'
        return pattern.format(
            year=date().year,
            filename=filename,
            owner=self.customer_company,
            instance=self
        )

    customer_signature = models.FileField(
        upload_to=customer_signature_path,
        verbose_name=_("Customer signature"),
        null=True,
        blank=True
    )

    # TODO: change path to files
    def provider_signature_path(self, filename):
        pattern = '{year}/{owner.id}/{filename}'
        return pattern.format(
            year=date().year,
            filename=filename,
            owner=self.provider_company,
            instance=self
        )

    provider_signature = models.FileField(
        upload_to=provider_signature_path,
        verbose_name=_("Provider signature"),
        null=True,
        blank=True
    )

    customer_signed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Customer signed at")
    )

    provider_signed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Provider signed at")
    )

    class Meta:
        abstract = True

    def __str__(self):
        return "{}, {}".format(self.provider_company, self.customer_company)

    def get_customer(self):
        return self.customer_company

    def get_provider(self):
        return self.provider_company

    @classmethod
    def get_master_company_lookup(cls, master_company):
        return Q(
            provider_company=master_company,
            provider_company__type=Company.COMPANY_TYPES.master) | \
            Q(
            customer_company=master_company,
            customer_company__type=Company.COMPANY_TYPES.master
        )

    def get_master_company(self):
        if self.provider_company.type == Company.COMPANY_TYPES.master:
            return self.provider_company.get_master_company()
        return self.customer_company.get_master_company()

    def get_closest_company(self):
        if self.provider_company.type == Company.COMPANY_TYPES.master:
            return self.provider_company
        return self.customer_company


class AbstractOrder(AbstractBaseOrder):

    total_with_tax = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Total with GST")
    )

    total = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Total")
    )

    tax = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0.00,
        verbose_name=_("GST")
    )

    currency = CurrencyField(
        verbose_name=_('Currency'),
        default=settings.DEFAULT_CURRENCY,
        choices=CURRENCY_CHOICES
    )

    class Meta:
        abstract = True

    def calculate_vat(self):
        vat = 0
        lines = getattr(self, '{}_lines'.format(self._meta.model_name))
        if lines:
            for group in lines.values('vat__rate').annotate(sum=Sum('amount')):
                vat += group['sum'] * group['vat__rate']
        return math.ceil(vat * 100) / 100

    def calculate_total(self):
        lines = getattr(self, '{}_lines'.format(self._meta.model_name))
        sum = lines.aggregate(sum=Sum('amount'))['sum'] or 0
        return math.ceil(sum * 100) / 100

    def save(self, *args, **kwargs):
        self.tax = self.calculate_vat()
        self.total = self.calculate_total()
        total_with_tax = self.tax + self.total
        self.total_with_tax = math.ceil(total_with_tax * 100) / 100
        super().save(*args, **kwargs)


class Order(AbstractOrder):

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    @workflow_function
    @workflow_function
    def is_state_50_available(self):
        return self._is_state_available(50)

    @workflow_function
    def is_state_90_available(self):
        return self._is_state_available(90)

    def _is_state_available(self, state_number):
        req_class = factory.get_instance('order_state_' + str(state_number))
        return req_class.check(self)

    def save(self, *args, **kwargs):
        just_added = self._state.adding
        super().save(*args, **kwargs)
        if just_added:
            self.create_state(10)


class AbstractOrderLine(UUIDModel):

    date = models.DateField(verbose_name=_("Date"))

    units = models.DecimalField(
        verbose_name=_("Units"),
        max_digits=8,
        decimal_places=2,
    )

    notes = models.TextField(verbose_name=_("Notes"))

    unit_price = models.DecimalField(
        verbose_name=_("Rate"),
        max_digits=8,
        decimal_places=2,
    )

    amount = models.DecimalField(
        verbose_name=_("Amount"),
        max_digits=8,
        decimal_places=2,
    )

    UNIT_TYPE_CHOICES = Choices(
        ('unit', _('Unit')),
    )

    unit_type = models.CharField(
        max_length=10,
        choices=UNIT_TYPE_CHOICES,
        default=UNIT_TYPE_CHOICES.unit
    )

    vat = models.ForeignKey(
        VAT,
        on_delete=models.PROTECT,
        verbose_name=_("VAT"),
    )

    def __str__(self):
        return self.name

    class Meta:
        abstract = True

    def get_tax(self):
        return self.vat.rate * self.unit_price

    def save(self, *args, **kwargs):
        self.amount = math.ceil(self.unit_price * self.units * 100) / 100
        super().save(*args, **kwargs)


class OrderLine(AbstractOrderLine):

    order = models.ForeignKey(
        Order,
        related_name="order_lines",
        on_delete=models.PROTECT,
        verbose_name=_("Order"),
    )

    class Meta:
        verbose_name = _("Order Line")
        verbose_name_plural = _("Order Lines")


class Invoice(AbstractOrder):

    is_paid = models.BooleanField(
        default=False,
        verbose_name=_("Is paid")
    )

    paid = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Paid sum")
    )

    paid_at = models.DateField(
        verbose_name=_("Paid at"),
        editable=False,
        null=True
    )

    myob_number = models.CharField(
        max_length=8,
        verbose_name=_("MYOB Number"),
        null=True
    )

    date = models.DateField(
        verbose_name=_("Creation date"),
        auto_now_add=True,
        null=True
    )

    updated = models.DateField(
        auto_now=True,
        null=True
    )

    number = models.CharField(
        verbose_name=_("Number"),
        max_length=20,
        null=True
    )

    order_number = models.TextField(
        verbose_name=_("Order Number"),
        null=True
    )

    period = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    separation_rule = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    approved = models.BooleanField(
        default=False
    )

    class Meta:
        verbose_name = _("Company Invoice")
        verbose_name_plural = _("Company Invoices")

    def __str__(self):
        return 'Invoice {} {}'.format(
            str(self.customer_company),
            date_format(self.date, settings.DATE_FORMAT)
        )

    def get_invoice_number(self, rule):
        invoice_number = ''

        if rule.serial_number:
            invoice_number += rule.serial_number

        starting_number = format(rule.starting_number, '08')
        invoice_number += starting_number

        return invoice_number

    def save(self, *args, **kwargs):
        just_added = self._state.adding

        if just_added:
            rule = self.provider_company.invoice_rules.first()
            self.number = self.get_invoice_number(rule)
            rule.starting_number += 1
            rule.save()

        super(Invoice, self).save(*args, **kwargs)


class InvoiceLine(AbstractOrderLine):

    invoice = models.ForeignKey(
        Invoice,
        related_name="invoice_lines",
        on_delete=models.PROTECT,
        verbose_name=_("Invoice"),
    )

    timesheet = models.ForeignKey(
        'hr.TimeSheet',
        related_name="invoice_lines",
        on_delete=models.CASCADE,
        verbose_name=_("TimeSheet"),
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _("Invoice Line")
        verbose_name_plural = _("Invoice Lines")

    def __str__(self):
        return '{}: {}'.format(
            str(self.invoice),
            date_format(self.date, settings.DATE_FORMAT)
        )


class Workflow(UUIDModel):
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=64
    )

    model = models.ForeignKey(
        ContentType,
        verbose_name=_("Binding model")
    )

    class Meta:
        verbose_name = _("Workflow")
        verbose_name_plural = _("Workflows")

    def __str__(self):
        return self.name

    @classmethod
    def is_owned(cls):
        return False


class WorkflowNode(UUIDModel):
    workflow = models.ForeignKey(
        Workflow,
        related_name="nodes",
        on_delete=models.PROTECT,
        verbose_name=_("Workflow")
    )

    number = models.PositiveSmallIntegerField(
        verbose_name=_("State number")
    )

    name_before_activation = models.CharField(
        verbose_name=_("State name before activation"),
        max_length=128
    )

    name_after_activation = models.CharField(
        verbose_name=_("State name after activation"),
        max_length=128,
        null=True,
        blank=True
    )

    active = models.BooleanField(
        verbose_name=_("Active"),
        default=True
    )

    rules = JSONField(
        verbose_name=_("Rules"),
        null=True,
        blank=True
    )

    company = models.ForeignKey(
        Company,
        related_name="company_wf_nodes",
        on_delete=models.PROTECT,
        verbose_name=_("Company")
    )

    hardlock = models.BooleanField(
        verbose_name=_("Hardlock"),
        default=False
    )

    endpoint = models.CharField(
        verbose_name=_("Endpoint to activate state"),
        max_length=255,
        null=True,
        blank=True
    )

    initial = models.BooleanField(
        verbose_name=_("Is initial state"),
        default=False
    )

    class Meta:
        verbose_name = _("Workflow Node")
        verbose_name_plural = _("Workflow Nodes")
        unique_together = ('company', 'number', 'workflow')

    def __str__(self):
        return "{}, {}, {}".format(self.workflow, self.name_before_activation, self.company)

    def save(self, *args, **kwargs):
        if not self.company:
            self.company = get_default_company()
        super().save(*args, **kwargs)

    def clean(self):
        self.validate_node(
            self.number, self.workflow, self.company, self.active, self.rules,
            self._state.adding, self.id or None
        )

    @classmethod
    def validate_node(cls, number, workflow, company, active,
                      rules, just_added, _id=None):
        system_company = get_default_company()
        system_node = None
        if company != system_company:
            system_node = WorkflowNode.objects.filter(
                company=system_company,
                workflow=workflow,
                number=number
            ).first()

            if system_node and system_node.hardlock:
                if active != system_node.active:
                    raise ValidationError(
                        _("Active for system node cannot be changed.")
                    )
                elif rules != system_node.rules:
                    raise ValidationError(
                        _("Rules for system node cannot be changed.")
                    )

        if not just_added:
            origin = WorkflowNode.objects.get(id=_id)
            number_changed = origin.number != number

            if company != system_company and system_node \
                    and system_node.hardlock and number_changed:
                raise ValidationError(
                    _("Number for system node cannot be changed.")
                )

            if number_changed:
                nodes = WorkflowNode.objects.filter(
                    company=company, workflow=workflow
                )
                is_used = [
                    node.rules and str(origin.number) in node.get_rule_states()
                    for node in nodes
                ]
                if any(is_used):
                    raise ValidationError(
                        _("Number is used in other node's rules.")
                    )

    def get_rule_states(self):
        if self.rules and "required_states" in self.rules:
            rule = self.rules["required_states"]
            return str(self._get_state_from_rule(rule))\
                .replace('[', '').replace(']', '').replace(' ', '').split(',')
        return ''

    def _get_state_from_rule(self, rule):
        if isinstance(rule, list):
            return self._get_state_from_list(rule[1:])
        elif isinstance(rule, int):
            return rule

    def _get_state_from_list(self, rules):
        return [self._get_state_from_rule(rule) for rule in rules]

    @classmethod
    def get_company_nodes(cls, company, workflow=None, nodes=None):
        default_company = get_default_company()

        queryset = nodes or cls.objects

        qry = Q(company=company, active=True)
        default_qry = Q(company=default_company, active=True)
        if workflow is not None:
            qry &= Q(workflow=workflow)
            default_qry &= Q(workflow=workflow)

        if default_company != company:
            company_numbers = list(
                queryset.filter(qry).values_list('number', flat=True)
            )
        else:
            company_numbers = []

        company_nodes = queryset.filter(
            qry | default_qry
        ).exclude(
            Q(number__in=company_numbers) & default_qry
        ).order_by('number')

        return company_nodes

    @classmethod
    def get_model_all_states(cls, model):
        states = cls.objects.filter(
            workflow__model=ContentType.objects.get_for_model(model)
        ).distinct('number').values(
            'number', 'name_before_activation', 'name_after_activation'
        )

        return [
            {'label': s['name_after_activation'] or s['name_before_activation'], 'value': s['number']} for s in states
        ]

    @classmethod
    def is_owned(cls):
        return False


class WorkflowObject(UUIDModel):
    object_id = models.UUIDField(
        verbose_name=_("Object id"),
        help_text=_("ID of Object belonging to model in Workflow")
    )

    state = models.ForeignKey(
        WorkflowNode,
        verbose_name=_("State"),
        related_name="states"
    )

    comment = models.TextField(
        verbose_name=_("Comments"),
        help_text=_("State Change Comment"),
        blank=True
    )

    active = models.BooleanField(
        verbose_name=_("Active"),
        default=True
    )

    score = models.SmallIntegerField(
        verbose_name=_("State score"),
        default=0
    )

    class Meta:
        verbose_name = _("Workflow object")
        verbose_name_plural = _("Workflow objects")

    def __str__(self):
        return str(self.state)

    @property
    def model_object(self):
        return self.get_model_object(self.state, self.object_id)

    @classmethod
    def get_model_object(cls, state, object_id):
        result = None
        model = state.workflow.model.model_class()
        try:
            result = model.objects.get(id=object_id)
        except Exception:
            pass
        return result

    def save(self, *args, **kwargs):
        is_raw = kwargs.pop('raw', False)
        if not is_raw:
            self.clean()

        just_added = self._state.adding

        lifecycle_enabled = kwargs.pop('lifecycle', True)

        if just_added and lifecycle_enabled:
            self.model_object.before_state_creation(self)

        super().save(*args, **kwargs)

        if just_added:
            if not is_raw:
                self.model_object.workflow(self.state)

            if lifecycle_enabled:
                self.model_object.after_state_created(self)

    def clean(self):
        self.validate_object(self.state, self.object_id, self._state.adding)

    @classmethod
    def validate_object(cls, state, object_id, just_added):
        model = state.workflow.model.model_class()
        try:
            model.objects.get(id=object_id)
        except Exception as e:
            raise ValidationError(e)

        model_object = cls.get_model_object(state, object_id)
        if state.company != model_object.get_closest_company() \
                and state.company != get_default_company():
            raise ValidationError(
                _("This state is not available for current object.")
            )

        if just_added and not model_object.is_allowed(state):
            raise ValidationError("{} {}".format(
                _('State creation is not allowed.'),
                model_object.get_required_message(state))
            )


class SiteCompany(
        UUIDModel,
        MasterCompanyLookupMixin):
    site = models.ForeignKey(
        Site,
        related_name="site_companies",
        on_delete=models.PROTECT,
        verbose_name=_("Site"),
    )
    company = models.ForeignKey(
        Company,
        related_name="site_companies",
        on_delete=models.PROTECT,
        verbose_name=_("Company")
    )

    class Meta:
        verbose_name = _("Site/Company relationship")
        verbose_name_plural = _("Site/Company relationships")
        unique_together = ('site', 'company')

    def __str__(self):
        return "{}: {}".format(self.site, self.company)

    @classmethod
    def get_master_company_lookup(cls, master_company):
        return Q(company=master_company)

    def get_master_company(self):
        return self.company.get_master_company()


class AbstractPayRuleMixin(models.Model):

    PERIOD_CHOICES = Choices(
        ('weekly', _('Weekly')),
        ('fortnightly', _('Fortnightly')),
        ('monthly', _('Monthly')),
        ('daily', _('Daily')),
    )

    period = models.CharField(
        max_length=11,
        verbose_name=_("Period"),
        choices=PERIOD_CHOICES,
        default=PERIOD_CHOICES.weekly
    )

    period_zero_reference = models.IntegerField(
        verbose_name=_("Period zero reference"),
        default=1
    )

    starting_number = models.IntegerField(
        verbose_name=_("Starting number"),
        default=1
    )

    comment = models.TextField(
        verbose_name=_("Comment"),
        null=True,
        blank=True
    )

    class Meta:
        abstract = True

    def clean(self):
        if ((self.period == AbstractPayRuleMixin.PERIOD_CHOICES.weekly and self.period_zero_reference > 7)
                or (self.period == AbstractPayRuleMixin.PERIOD_CHOICES.fortnightly and self.period_zero_reference > 14)
                or (self.period == AbstractPayRuleMixin.PERIOD_CHOICES.monthly and self.period_zero_reference > 29)):
            raise ValidationError(_('Incorrect period zero reference'))


class InvoiceRule(AbstractPayRuleMixin, UUIDModel):

    company = models.ForeignKey(
        Company,
        related_name="invoice_rules",
        verbose_name=_("Company"),
        on_delete=models.CASCADE
    )

    serial_number = models.CharField(
        max_length=20,
        verbose_name=_("Serial number"),
        null=True,
        blank=True
    )

    notice = models.TextField(
        verbose_name=_("Notice"),
        null=True,
        blank=True
    )

    SEPARATION_CHOICES = Choices(
        ('one_invoce', _('One invoce')),
        ('per_jobsite', _('Per jobsite')),
        ('per_candidate', _('Per candidate')),
    )

    separation_rule = models.CharField(
        max_length=13,
        verbose_name=_("Separation rule"),
        choices=SEPARATION_CHOICES,
        default=SEPARATION_CHOICES.one_invoce
    )

    show_candidate_name = models.BooleanField(
        verbose_name=_("Show Candidate Name"),
        default=False
    )

    @property
    def last_invoice_created(self):
        date = None

        if self.company.customer_invoices.exists():
            date = self.company.customer_invoices.order_by('-date')[0].date

        return date

    @property
    def last_invoice_updated(self):
        date = None

        if self.company.customer_invoices.exists():
            date = self.company.customer_invoices.order_by('-updated')[0].updated

        return date

    class Meta:
        verbose_name = _("Invoice Rule")
        verbose_name_plural = _("Invoice Rules")
        unique_together = ('company', 'serial_number')


class CurrencyExchangeRates(UUIDModel):
    from_currency = CurrencyField(
        verbose_name=_('From currency'),
        default='USD',
        choices=CURRENCY_CHOICES
    )
    to_currency = CurrencyField(
        verbose_name=_('To currency'),
        default='USD',
        choices=CURRENCY_CHOICES
    )
    exchange_rate = models.DecimalField(
        verbose_name=_('Exchange rate'),
        decimal_places=12,
        max_digits=18,
        default=1,
    )

    class Meta:
        verbose_name = _("Currency Exchange Rate")
        verbose_name_plural = _("Currency Exchange Rates")
        unique_together = ('from_currency', 'to_currency')

    @classmethod
    def is_owned(cls):
        return False


class TemplateMessage(UUIDModel):

    INVALID_DEEP_MESSAGE = _("Max level deep: %s")

    INTERPOLATE_START = '[['
    INTERPOLATE_END = ']]'
    DELIMITER = '__'
    MAX_LEVEL_DEEP = 5

    TYPE_CHOICES = ()

    name = models.CharField(
        max_length=256,
        default="",
        verbose_name=_("Name"),
        db_index=True
    )

    slug = models.SlugField()

    type = models.CharField(
        max_length=8,
        choices=TYPE_CHOICES,
        verbose_name=_("Type")
    )

    subject_template = models.CharField(
        max_length=256,
        default="",
        verbose_name=_("Subject template"),
        blank=True
    )

    message_text_template = models.TextField(
        default="",
        verbose_name=_("Text template"),
        blank=True
    )

    message_html_template = models.TextField(
        default="",
        verbose_name=_("HTML template"),
        blank=True
    )

    reply_timeout = models.IntegerField(
        default=10,
        verbose_name=_("Reply timeout"),
        help_text=_("Minutes")
    )

    delivery_timeout = models.IntegerField(
        default=10,
        verbose_name=_("Delivery timeout"),
        help_text=_("Minutes")
    )

    company = models.ForeignKey(
        Company,
        verbose_name=_("Master company"),
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    class Meta:
        abstract = True
        unique_together = ('name', 'company', 'type')

    def __str__(self):
        return self.name

    @classmethod
    def is_owned(cls):
        return False

    def clean(self):
        """
        Clean all template layers
        """
        for field in ['message_html_template',
                      'message_text_template',
                      'subject_template']:
            if getattr(self, field):
                arguments = self.get_require_params(
                    getattr(self, field), use_lookup=True
                )
                for a in arguments:
                    if len(a.split(self.DELIMITER)) - 1 > self.MAX_LEVEL_DEEP:
                        raise ValidationError(
                            {field: self.INVALID_DEEP_MESSAGE % self.MAX_LEVEL_DEEP}
                        )

    def compile(self, **params):
        """
        Template compilation, variables substitution.
        Use params dict to pass variables into the template.
        Example:
            params = {
                'user': {'first_name': 'John',
                        'last_name': 'Davidson',
                        'contact': contact_instance},
                'starts_at': datetime.now(),
                'contact': Contact.objects.last()
            }
        """
        subject_compiled, text_compiled, html_compiled = self.compile_string(
            self.subject_template,
            self.message_text_template,
            self.message_html_template,
            **params)

        return {
            'id': self.id,
            'text': text_compiled,
            'html': html_compiled,
            'subject': subject_compiled
        }

    @classmethod
    def get_dict_values(cls, params, *rows, use_lookup=True):
        """Return dict with parsed variables as keys and params as its values.

        :param params: dict of variables
        :param rows: list of templates
        :param use_lookup: using lookup notation

        :return: dict
        """

        values_dict = dict()

        for parsed_item in cls.get_require_params(*rows, use_lookup=use_lookup):

            if parsed_item in params:
                values_dict.setdefault(parsed_item, params.get(parsed_item))

            split_parameter = parsed_item.split(cls.DELIMITER)[:cls.MAX_LEVEL_DEEP]

            parameter = ""
            special_parameter = split_parameter[0]

            for p in list(split_parameter):

                if special_parameter in params:
                    split_parameter = [special_parameter] + split_parameter[1:]
                    break
                split_parameter = split_parameter[1:]
                if parameter:
                    parameter = '{}{}{}'.format(parameter, cls.DELIMITER, p)
                else:
                    parameter = '{}'.format(parameter)
                if len(split_parameter) == 0:
                    break
                special_parameter = '{}{}{}'.format(
                    special_parameter,
                    cls.DELIMITER,
                    split_parameter[0]
                )

            if len(split_parameter) == 0:
                continue

            value = params[split_parameter[0]]

            for index, t in enumerate(split_parameter):
                parameter = '{}{}'.format(parameter, t)
                values_dict.setdefault(parameter, value)
                if len(split_parameter) - 1 == index:
                    continue

                key = split_parameter[index + 1]

                # handler
                if isinstance(value, collections.Iterable) and not hasattr(value, key):
                    try:
                        value = value[key]
                    except Exception:
                        break
                else:
                    if key not in ['delete', 'save', 'update', 'fetch_remote']:
                        if hasattr(value, key):
                            value = getattr(value, key)
                        else:
                            break

                # checking for callable
                if callable(value):
                    value = value()

                parameter = '{}{}'.format(parameter, cls.DELIMITER)
        return values_dict

    @classmethod
    def get_require_params(cls, *rows, use_lookup=True):
        """Get all variable names from multiple templates.
        Use use_lookup=False to disable lookups (lookup will parse
         variable like user__first_name).

        :param rows: templates list
        :param use_lookup: bool - using lookup notation, default True

        :return: set of names variables'
        """
        pattern = '{start}\\s*{pattern}\\s*{end}'.format(
            start=re.escape(cls.INTERPOLATE_START),
            pattern='(?P<param>[a-z]{1}[a-z\_0-9]*)',
            end=re.escape(cls.INTERPOLATE_END)
        )

        # get all param names
        parsed_params = set()
        for r in rows:
            parsed_params |= set(re.findall(pattern, r, re.I))

        if not use_lookup:
            parsed_params = map(lambda x: x.split(cls.DELIMITER)[0], parsed_params)

        return set(parsed_params)

    @classmethod
    def compile_string(cls, *raw_strings, **params):
        """Replace variables on param values.

        :param raw_strings: templates list
        :param params: variables dict
        :return: compiled rows
        """

        raw_strings = list(raw_strings)

        values_dict = cls.get_dict_values(params, *raw_strings)
        for param, value in values_dict.items():
            pattern = "{start}\\s*{param}\\s*{end}".format(
                start=re.escape(cls.INTERPOLATE_START),
                end=re.escape(cls.INTERPOLATE_END),
                param=param
            )

            value = str(value)
            for index, r in enumerate(raw_strings):
                raw_strings[index] = re.sub(pattern, value, r)

        return raw_strings

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)


class PublicHoliday(UUIDModel):
    """
    Public holiday model
    """

    country = models.ForeignKey('core.Country', verbose_name=_("Country"))
    date = models.DateField(_("Date"))
    name = models.CharField(_("Name"), max_length=512)

    class Meta:
        ordering = ['country', 'date']
        verbose_name = _("Public holiday")
        verbose_name_plural = _("Public holidays")

    @classmethod
    def is_holiday(cls, date, country=None):
        if country is None:
            country = Country.objects.get(code2='AU')
        return cls.objects.filter(country=country, date=date).exists()

    @classmethod
    def is_owned(cls):
        return False


class ExtranetNavigation(MPTTModel, UUIDModel):
    CLIENT = 'client'
    MANAGER = 'manager'
    CANDIDATE = 'candidate'
    ACCESS_LEVEL_CHOICES = Choices(
        (CLIENT, _('Client')),
        (MANAGER, _('Manager')),
        (CANDIDATE, _('Candidate'))
    )

    id = models.AutoField(auto_created=True, primary_key=True,
                          serialize=False, verbose_name='ID')
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True)
    name = models.CharField(max_length=63, verbose_name=_("Menu Title"))
    url = models.CharField(max_length=63, verbose_name=_("Default Url"))
    endpoint = models.CharField(max_length=63, verbose_name=_("DRF Endpoint"))
    access_level = models.CharField(max_length=63, choices=ACCESS_LEVEL_CHOICES,
                                    default=MANAGER, verbose_name=_("Acess Level"))

    class Meta:
        verbose_name = _("Extranet Navigation")
        verbose_name_plural = _("Extranet Navigations")

    def __str__(self):
        return self.name

    @classmethod
    def is_owned(cls):
        return False


class Role(UUIDModel):
    ROLE_NAMES = Choices(
        ('candidate', _('Candidate')),
        ('manager', _('Manager')),
        ('client', _('Client')),
        ('trial', _('Trial')),
    )

    name = models.CharField(max_length=255, choices=ROLE_NAMES)

    company_contact_rel = models.ForeignKey(
        CompanyContactRelationship,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name=_('Company Contact Relation'),
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name

    @classmethod
    def is_owned(cls):
        return False


connect_default_signals(Country)
connect_default_signals(Region)
connect_default_signals(City)

__all__ = [
    'UUIDModel',
    'WorkflowObject', 'Workflow', 'WorkflowNode',
    'Contact', 'ContactUnavailability',
    'User', 'UserManager',
    'Country', 'Region', 'City',
    'Company', 'CompanyContact', 'CompanyRel', 'CompanyContactRelationship', 'CompanyContactAddress',
    'CompanyAddress', 'CompanyLocalization', 'CompanyTradeReference', 'BankAccount', 'SiteCompany',
    'Address', 'FileStorage',
    'Order',
    'AbstractPayRuleMixin', 'Invoice', 'InvoiceLine',
    'Note', 'Tag',
    'VAT', 'InvoiceRule',
    'CurrencyExchangeRates', 'TemplateMessage',
    'PublicHoliday', 'ExtranetNavigation',
    'AbstractBaseOrder', 'AbstractOrder', 'Role'
]
