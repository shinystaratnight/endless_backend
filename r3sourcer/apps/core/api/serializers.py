from itertools import chain
from collections import OrderedDict

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.validators import validate_email
from django.db import models
from django.utils import six, timezone
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _
from phonenumber_field import phonenumber
from rest_framework import serializers, exceptions
from rest_framework.fields import empty

from django.db.models.fields.related import (
    RelatedField, ManyToOneRel, ManyToManyField, ManyToManyRel, OneToOneRel
)
from django.contrib.contenttypes.fields import GenericRelation

from r3sourcer.apps.core import models as core_models
from r3sourcer.apps.core.workflow import (NEED_REQUIREMENTS, ALLOWED, ACTIVE, VISITED, NOT_ALLOWED)
from r3sourcer.apps.core.api import mixins as core_mixins, fields as core_field

rest_settings = settings.REST_FRAMEWORK

RELATED_NONE, RELATED_DIRECT, RELATED_FULL = 'minimal', 'direct', 'full'


class ApiFullRelatedFieldsMixin():
    """
    Use Meta of the serializer class to render related objects

    Settings:
    ``settings.REST_FRAMEWORK['RELATED_FULL']`` (default: 'minimal') - render related object
    values: 'full', 'direct', 'minimal'
    """

    _read_only_fields = ('__str__', )

    def __init__(self, *args, **kwargs):
        parent_field_name = kwargs.pop('parent_name', None)
        context = kwargs.get('context', {})
        related_obj_setting = context.get(
            'related_setting') or kwargs.get('related_setting')

        super(ApiFullRelatedFieldsMixin, self).__init__(*args, **kwargs)

        data = kwargs.get('data', empty)
        request = context.get('request')

        if not hasattr(self, 'Meta'):
            return

        related_obj_setting = related_obj_setting or \
            getattr(self.Meta, 'related', rest_settings.get(
                'RELATED', RELATED_NONE))
        related_obj_setting = related_obj_setting or RELATED_NONE
        internal_fields_dict = getattr(self.Meta, 'related_fields', {})
        related_setting = related_obj_setting if related_obj_setting != RELATED_DIRECT else RELATED_NONE

        for field_name, field in self.fields.items():
            if field_name == 'id':
                kwargs = field._kwargs
                kwargs['required'] = False
                kwargs['read_only'] = False
                self.fields[field_name] = field.__class__(
                    *field._args, **kwargs
                )
                continue

            if field_name in self._read_only_fields:
                field_kwargs = {}
                if field_name == '__str__':
                    label = parent_field_name.title().replace('_', ' ') \
                        if parent_field_name \
                        else self.Meta.model._meta.verbose_name.title()
                    field_kwargs['label'] = label
                self.fields[field_name] = serializers.ReadOnlyField(
                    **field_kwargs
                )
                continue

            is_field_in_data = data is not empty and field_name in data
            is_pk_data = is_field_in_data and not isinstance(data[field_name], (list, dict))
            is_id_partial = kwargs.get('partial', False) or bool(
                is_field_in_data and isinstance(data[field_name], dict) and data[field_name].get('id')
            )

            if is_id_partial and is_field_in_data and isinstance(data[field_name], list):
                internal_fields_dict[field_name] = [f for f in data.get(field_name, [])]

            if not is_pk_data and isinstance(data, list) and len(data) > 0:
                data_elem = data[0]
                if isinstance(data_elem, dict):
                    is_pk_data = data_elem.get(field_name) and \
                        not isinstance(data_elem[field_name], (list, dict))
                else:
                    is_pk_data = True

            if isinstance(field, serializers.DateTimeField):
                self.fields[field_name] = core_field.ApiDateTimeTzField(
                    *field._args, **field._kwargs
                )
                continue
            if isinstance(field, serializers.ChoiceField):
                self.fields[field_name] = core_field.ApiChoicesField(
                    *field._args, **field._kwargs
                )
                continue
            elif isinstance(field, serializers.ImageField):
                self.fields[field_name] = core_field.ApiContactPictureField(
                    *field._args, **field._kwargs
                )
                continue
            elif isinstance(field, serializers.FileField):
                self.fields[field_name] = core_field.ApiBase64FileField(
                    *field._args, **field._kwargs
                )
                continue
            elif isinstance(field, serializers.ModelSerializer):
                if is_pk_data:
                    self.fields[field_name] = self._get_id_related_field(
                        field, field.Meta.model.objects
                    )
                elif isinstance(field, ApiBaseModelSerializer):
                    continue
                else:
                    context['related_setting'] = related_setting
                    kwargs = dict(
                        required=field.required,
                        allow_null=field.allow_null,
                        read_only=field.read_only,
                        context=context,
                        many=getattr(field, 'many', False),
                        data=data.get(field_name, empty) if data is not empty else empty,
                        parent_name=parent_field_name or field_name,
                        partial=is_id_partial,
                    )

                    internal = self._get_internal_serializer(
                        field_name, field, field.Meta.model,
                        related_setting, internal_fields_dict
                    )
                    self.fields[field_name] = internal(**kwargs)
                continue

            try:
                related_field = self.Meta.model._meta.get_field(field_name)
            except FieldDoesNotExist:
                continue

            is_many_to_one_relation = isinstance(related_field, ManyToOneRel)
            is_one_to_one_relation = isinstance(related_field, OneToOneRel)
            if not isinstance(related_field, RelatedField) and not is_many_to_one_relation:
                if getattr(related_field, 'blank', False) and not getattr(related_field, 'null', False):
                    self.fields[field_name] = core_field.EmptyNullField.from_field(
                        field)

                continue

            is_generic_relation = isinstance(related_field, GenericRelation)
            is_many_relation = is_generic_relation or (is_many_to_one_relation and not is_one_to_one_relation)

            if is_many_to_one_relation:
                rel_model = related_field.related_model
            else:
                rel_model = related_field.rel.model

            if data is not empty or (request is not None and request.method in ('POST', 'PUT', 'PATCH')):
                if is_pk_data or (data is empty and related_obj_setting == RELATED_NONE and not is_many_relation):
                    kwargs = {'field': field}
                    if is_pk_data:
                        kwargs.update(read_only=False,
                                      queryset=rel_model.objects)

                    self.fields[field_name] = self._get_id_related_field(
                        **kwargs
                    )
                    continue
            if data is empty and related_obj_setting == RELATED_NONE and not is_many_relation and \
                    field_name not in internal_fields_dict:
                self.fields[field_name] = core_field.ApiBaseRelatedField(
                    read_only=True,
                    many=isinstance(
                        related_field, (ManyToManyRel, ManyToManyField)),
                )
                continue

            if self.Meta.model is rel_model and (
                data is empty or data.get(field_name) is None
            ):
                continue  # pragma: no cover

            if not isinstance(data, list) and data is not empty and not field.read_only:
                related_data = data.get(field_name, empty)
            else:
                related_data = empty

            if isinstance(related_data, list):
                related_data = [
                    {'id': related_item} if isinstance(related_item, str) else related_item
                    for related_item in related_data
                ]

            kwargs = dict(
                required=field.required and not is_many_relation,
                allow_null=field.allow_null,
                read_only=field.read_only,
                context=context,
                many=is_many_relation,
                data=related_data,
                parent_name=parent_field_name or field_name,
                partial=is_id_partial,
            )

            internal = self._get_internal_serializer(
                field_name, field, rel_model,
                related_setting, internal_fields_dict
            )

            kwargs['context']['related_setting'] = internal.Meta.related
            self.fields[field_name] = internal(**kwargs)

    def _get_internal_serializer(self, field_name, field, model,
                                 related_setting, internal_fields_dict):
        related_fields = internal_fields_dict.get(field_name, [])
        if not isinstance(related_fields, (list, tuple)) or not related_fields:
            related_fields = '__all__'

        internal_meta = type('Meta', (object,), dict(
            model=model,
            fields=related_fields,
            related=related_setting
        ))

        internal = type(
            '{}InternalSerializer'.format(model.__name__),
            (ApiBaseModelSerializer,),
            dict(Meta=internal_meta)
        )

        return internal

    def _get_id_related_field(self, field, queryset=None, read_only=None):
        if hasattr(field, 'child_relation'):
            child_queryset = field.child_relation.get_queryset()
            queryset = queryset if child_queryset is None else child_queryset

        read_only = read_only if read_only is not None else field.read_only

        return serializers.SlugRelatedField(
            slug_field='id',
            queryset=field._kwargs.get('queryset') or queryset,
            required=field.required,
            allow_null=field.allow_null,
            read_only=read_only,
        )

    def create(self, validated_data):
        for field_name, field in self.fields.items():
            if isinstance(field, serializers.ModelSerializer):
                model = field.Meta.model
                instance = validated_data.pop(field_name, None)
                if instance is None:
                    continue

                if not isinstance(instance, model):
                    instance = model.objects.create(**instance)
                validated_data[field_name] = instance

        obj = self.Meta.model.objects.create(**validated_data)
        return obj

    def update(self, obj, validated_data):
        for field_name, field in self.fields.items():
            if isinstance(field, serializers.ModelSerializer):
                model = field.Meta.model
                instance = validated_data.pop(field_name, None)
                if instance is None:
                    continue

                if not isinstance(instance, model):  # pragma: no cover
                    instance_id = instance.get('id')
                    if instance_id:
                        instance, _ = model.objects.update_or_create(id=instance_id, defaults=instance)
                    else:
                        instance = model.objects.create(**instance)

                if not isinstance(getattr(obj.__class__, field_name, None), property):
                    setattr(obj, field_name, instance)

        return super(ApiFullRelatedFieldsMixin, self).update(obj, validated_data)


class ApiRelatedFieldManyMixin:

    # Format: {'many_related_field': 'related_field_name'}
    many_related_fields = None

    def create(self, validated_data):
        if self.many_related_fields:
            related_data = {
                field: validated_data.pop(field)
                for field in self.many_related_fields.keys()
                if validated_data.get(field)
            }
        else:
            related_data = {}

        instance = super().create(validated_data)
        related_data['id'] = instance.id

        self.create_many(related_data)
        return instance

    def create_many(self, validated_data):
        for field_name, related_name in self.many_related_fields.items():
            field = self.fields.get(field_name)

            if isinstance(field, serializers.ListSerializer) and not field.read_only:
                model = field.child.Meta.model
                instances = validated_data.pop(field_name, [])

                for instance in instances:
                    if instance is not None and not isinstance(instance, model):
                        instance[related_name + '_id'] = validated_data['id']
                        model.objects.create(**instance)

    def update(self, instance, validated_data):
        if self.many_related_fields:
            related_data = {
                field: validated_data.pop(field)
                for field in self.many_related_fields.keys()
                if field in validated_data
            }
        else:
            related_data = {}

        instance = super().update(instance, validated_data)
        related_data['id'] = instance.id

        self.update_many(instance, related_data)
        return instance

    def update_many(self, instance, validated_data):
        """
        Update related objects
        """
        for field_name, related_name in self.many_related_fields.items():
            field = self.fields.get(field_name)

            if isinstance(field, serializers.ListSerializer) and not field.read_only:
                instances = validated_data.get(field_name, [])

                objects = getattr(instance, field_name)
                for item in instances:
                    item[related_name + '_id'] = instance.id
                    if item.get('id'):
                        obj = objects.filter(id=item['id'])
                        obj.update(**item)
                    else:
                        model = field.child.Meta.model
                        model.objects.create(**item)


class ApiMethodFieldsMixin():
    method_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        method_fields = self.get_method_fields()
        for method_field in method_fields:
            field_kwargs = {}
            if isinstance(method_field, (list, tuple)) and len(method_field) == 2:
                field_kwargs['method_name'] = method_field[1]
                method_field = method_field[0]
            elif not isinstance(method_field, six.string_types):
                message = (
                    'Field data {!r} not supported. '
                    'Method fields can be declared as list or tuple of field name '
                    'strings or 2-item tuples in form (field_name, method_name)'
                )
                raise Exception(message.format(method_field))
            self.fields[method_field] = serializers.SerializerMethodField(
                **field_kwargs)

    def get_method_fields(self):
        return self.method_fields or []


class ApiFieldsMixin():

    required_fields = {'request', 'id'}

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', [])

        if fields:
            self._declared_fields = OrderedDict([
                (name, field)
                for name, field in self._declared_fields.items()
                if name in fields
            ])

            allowed = set(fields)
            required = set(self.get_required_fields()) or set()
            possible_fields = allowed | required | set(self._declared_fields)

            if hasattr(self, 'Meta'):
                meta_parents = (self.Meta, )

                serializer_fields = set(self.get_fields().keys()) \
                    if self.Meta.fields == '__all__' else set(self.Meta.fields)
                fields_set = serializer_fields & possible_fields
                if '__str__' in serializer_fields:
                    fields_set.add('__str__')

                meta_attrs = {
                    'fields': list(fields_set)
                }
                Meta = type('Meta', meta_parents, meta_attrs)

                self.Meta = Meta

        super(ApiFieldsMixin, self).__init__(*args, **kwargs)

        if fields:
            existing = set(self.fields.keys())
            for field_name in existing - possible_fields:
                self.fields.pop(field_name)

    def get_required_fields(self):
        return self.required_fields


class ApiContactImageFieldsMixin():
    image_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        image_fields = self.image_fields or []
        for image_field in image_fields:
            self.fields[image_field] = core_field.ApiContactPictureField(required=False)


class MetaFields(serializers.SerializerMetaclass):

    def __new__(cls, name, bases, namespace, **kwargs):
        res_cls = super().__new__(cls, name, bases, namespace)

        if hasattr(res_cls, 'Meta'):
            super_meta = cls._get_super_meta(bases)
            meta_parents = (res_cls.Meta, )
            if super_meta:
                meta_parents += (super_meta, )

            Meta = type('Meta', meta_parents, {})

            fields = getattr(Meta, 'fields', [])
            if fields == '__all__' or '__all__' in fields:
                model = getattr(Meta, 'model')
                all_fields = model._meta.get_fields() if model is not None else []
                all_fields = [
                    field.name for field in all_fields
                    if (
                        ((not hasattr(field, 'field') and getattr(field, 'related_name', None) is None) or
                         isinstance(field, models.OneToOneRel)) and
                        not isinstance(field, GenericForeignKey)
                    )
                ]
                fields = chain(
                    all_fields, [field for field in fields if isinstance(field, dict)])

            if fields:
                serializer_fields = []
                related_fields = {}
                for field in fields:
                    if isinstance(field, dict):
                        related_fields.update(field)
                        serializer_fields.extend(field.keys())
                        continue

                    serializer_fields.append(field)

                if '__str__' not in serializer_fields:
                    serializer_fields.append('__str__')

                Meta.fields = serializer_fields
                if related_fields:
                    Meta.related_fields = related_fields

                res_cls.Meta = Meta

        return res_cls

    @classmethod
    def _get_super_meta(cls, bases):
        for base_cls in bases:
            if hasattr(base_cls, 'Meta'):
                return base_cls.Meta


@six.add_metaclass(MetaFields)
class ApiBaseModelSerializer(
        ApiMethodFieldsMixin,
        ApiFullRelatedFieldsMixin,
        ApiFieldsMixin,
        serializers.ModelSerializer):

    pass


class AddressSerializer(ApiBaseModelSerializer):
    class Meta:
        model = core_models.Address
        fields = '__all__'

    def validate_state(self, value):
        if not value:
            return

        country = self.initial_data.get('country')
        if value and str(value.country.id) != country:
            raise serializers.ValidationError(
                "Country has no '%s' state" % value.name)
        return value

    def validate_city(self, value):
        if not value:
            return

        state = self.initial_data.get('state')
        if state and str(value.region.id) != state:
            raise serializers.ValidationError(
                "State has no '%s' city" % value.name)

        country = self.initial_data.get('country')
        if value and str(value.country.id) != country:
            raise serializers.ValidationError(
                "Country has no '%s' city" % str(value))

        return value


class UserSerializer(ApiBaseModelSerializer):

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = self.Meta.model()
        user.set_password(password)
        user.save()
        return user

    class Meta:
        model = get_user_model()
        fields = 'password',


class CompanyContactSerializer(ApiBaseModelSerializer):

    def create(self, validated_data):
        contact = validated_data.get('contact', None)
        if not isinstance(contact, core_models.Contact):
            raise exceptions.ValidationError("Contact is required")

        instance = super(CompanyContactSerializer, self).create(validated_data)
        return instance

    def process_approve(self, instance):
        now = timezone.now()
        request = self.context['request']
        approved_by_staff = self.context['approved_by_staff']
        approved_by_primary_contact = self.context['approved_by_primary_contact']

        if approved_by_staff:
            instance.approved_by_staff = request.user.contact
            instance.staff_approved_at = now

        if approved_by_primary_contact:
            instance.approved_by_primary_contact = request.user.contact
            instance.primary_contact_approved_at = now

    class Meta:
        model = core_models.CompanyContact
        fields = ('id', 'job_title', 'rating_unreliable', 'contact',
                  'legacy_myob_card_number', 'voip_username', 'voip_password',
                  'receive_job_confirmation_sms')
        related = RELATED_DIRECT


class ContactUnavailabilitySerializer(ApiBaseModelSerializer):
    class Meta:
        model = core_models.ContactUnavailability
        fields = ('id', 'contact', 'unavailable_from', 'unavailable_until',
                  'notes',)
        related = RELATED_DIRECT


class NoteSerializer(core_mixins.CreatedUpdatedByMixin, ApiBaseModelSerializer):

    class Meta:
        model = core_models.Note
        fields = ('__all__', )


class ContactSerializer(ApiContactImageFieldsMixin, ApiBaseModelSerializer):
    company_contact = CompanyContactSerializer(many=True, read_only=True)

    image_fields = ('picture', )
    many_related_fields = {
        'company_contact': 'contact',
    }

    method_fields = ('job_title', 'availability', 'is_candidate_contact', 'is_company_contact', 'master_company')

    def get_job_title(self, obj):
        return obj.get_job_title() if obj and obj.is_company_contact() else None

    def get_availability(self, obj):
        return obj.get_availability() if obj else None

    def get_is_candidate_contact(self, obj):
        return obj.is_candidate_contact() if obj else None

    def get_is_company_contact(self, obj):
        return obj.is_company_contact() if obj else None

    def get_master_company(self, obj):
        master_company = obj.get_closest_company()
        return master_company and core_field.ApiBaseRelatedField.to_read_only_data(master_company)

    def to_representation(self, instance):
        data = super(ContactSerializer, self).to_representation(instance)
        data['id'] = instance.pk
        return data

    def create(self, validated_data):
        address = validated_data.pop('address', None)
        if not isinstance(address, core_models.Address):
            try:
                address = core_models.Address.objects.create(**address)
            except (ValidationError, TypeError) as e:
                raise serializers.ValidationError(getattr(e, 'messages', _('Cannot create Contact without address')))
        contact = core_models.Contact.objects.create(
            address=address, **validated_data)
        return contact

    def validate(self, data):
        if not data['email'] and not data['phone_mobile']:
            raise serializers.ValidationError(
                _('Please specify E-mail and/or Mobile Phone'))
        return data

    class Meta:
        model = core_models.Contact
        read_only = ('is_available', 'address', 'company_contact', 'object_history', 'notes')
        fields = (
            'title', 'first_name', 'last_name', 'email', 'phone_mobile', 'gender', 'is_available', 'marital_status',
            'birthday', 'spouse_name', 'children', 'picture', 'address', 'phone_mobile_verified', 'email_verified',
            'id',
            # FIXME: change related fields
            {
                'user': ('id',),
                'notes': ('id', 'note'),
                'company_contact': (
                    'id', 'job_title', 'rating_unreliable', 'legacy_myob_card_number', 'voip_username',
                    'voip_password', 'receive_job_confirmation_sms'
                ),
                'candidate_contacts': ('id', 'recruitment_agent'),
            }
        )
        related = RELATED_DIRECT
        extra_kwargs = {
            'candidate_contacts': {'read_only': True},
            'company_contact': {'read_only': True},
            'master_company': {'read_only': True},
            'user': {'read_only': True},
        }


class ContactPasswordSerializer(UserSerializer):
    password1 = serializers.CharField(required=True)

    def validate(self, data):
        password = data['password']
        password1 = data['password1']

        if password != password1:
            raise exceptions.ValidationError(_('Passwords does not match'))

        validate_password(password, None)

        return data

    class Meta:
        model = get_user_model()
        fields = ('password', 'password1')


class ContactRegisterSerializer(ContactSerializer):

    def create(self, validated_data):
        # FIXME: change password handling
        user = UserSerializer().create({'password': ''})

        validated_data['user'] = user
        contact = super().create(validated_data)

        return contact

    class Meta:
        fields = (
            'title', 'first_name', 'last_name', 'email', 'phone_mobile',
            {
                'address': ('country', 'state', 'city', 'street_address',
                            'postal_code'),
            }
        )


class CompanySerializer(serializers.ModelSerializer):
    # TODO: Permission related issue: Some fields need to be checked depending on
    # TODO: company type when updated or created and role initialed action, for example parent field

    def to_representation(self, instance):
        data = super(CompanySerializer, self).to_representation(instance)
        data['id'] = instance.pk
        return data

    class Meta:
        model = core_models.Company
        fields = 'name', 'business_id', 'registered_for_gst', 'tax_number', 'website',\
                 'date_of_incorporation', 'description', 'notes', 'bank_account',\
                 'credit_check', 'credit_check_date', 'terms_of_payment',\
                 'payment_due_date', 'available', 'billing_email', 'credit_check_proof',\
                 'type', 'company_rating'


class CompanyContactRelationshipSerializer(ApiBaseModelSerializer):

    class Meta:
        model = core_models.CompanyContactRelationship
        fields = ('__all__', {
            'company_contact': ('id', 'job_title', 'receive_job_confirmation_sms', {
                'contact': ('id', 'first_name', 'last_name', 'phone_mobile', 'email')
            })
        })


class CompanyContactRenderSerializer(CompanyContactSerializer):

    method_fields = ('company', 'manager')

    def get_company(self, instance):
        rel = instance.relationships.first()
        if rel is not None:
            return CompanyListSerializer(rel.company).data
        return None

    def get_manager(self, instance):
        company = self.get_company(instance)
        return company and company['manager']

    class Meta:
        model = core_models.CompanyContact
        fields = ('id', 'job_title', 'rating_unreliable', 'contact',
                  'legacy_myob_card_number', 'voip_username', 'voip_password',
                  'receive_job_confirmation_sms')
        related = RELATED_DIRECT


class CompanyContactRegisterSerializer(ContactRegisterSerializer):

    company = CompanySerializer(required=False)

    def create(self, validated_data):
        company = validated_data.pop('company', None)

        contact = super().create(validated_data)

        company_contact = CompanyContactSerializer().create(
            {'contact': contact})

        if isinstance(company, dict):
            self.fields['company'].is_valid(raise_exception=True)
            company = self.fields['company'].save()

        CompanyContactRelationshipSerializer().create({
            'company_contact': company_contact,
            'company': company,
        })

        return company_contact

    class Meta:
        fields = (
            'title', 'first_name', 'last_name', 'email', 'phone_mobile',
            {
                'address': ('country', 'state', 'city', 'street_address',
                            'postal_code'),
                'company': ('name', 'business_id'),
            },
        )


class CompanyAddressSerializer(core_mixins.WorkflowStatesColumnMixin, ApiBaseModelSerializer):
    method_fields = ('portfolio_manager', 'invoices_count', 'orders_count')

    class Meta:
        model = core_models.CompanyAddress

    def get_company_rel(self, obj):
        company = obj.company
        company_rel = cache.get('company_rel_{}'.format(company.id), None)
        if not company_rel:
            current_site = get_current_site(self.context.get('request'))

            site_company = core_models.SiteCompany.objects.filter(
                site=current_site,
                company__master_companies__regular_company=company
            ).last()
            master_type = core_models.Company.COMPANY_TYPES.master
            if not site_company or site_company.company.type != master_type:
                return

            company_rel = company.regular_companies.filter(
                master_company=site_company.company
            ).last()

            cache.set('company_rel_{}'.format(company.id), company_rel)
        return company_rel

    def get_portfolio_manager(self, obj):
        if not obj:
            return

        company_rel = self.get_company_rel(obj)
        if not company_rel:
            return

        if company_rel:
            return CompanyContactSerializer(company_rel.primary_contact).data

    def get_active_states(self, obj):
        if obj:
            obj = self.get_company_rel(obj)

        return super().get_active_states(obj)

    def get_invoices_count(self, obj):
        if not obj:
            return 0

        return obj.company.customer_invoices.all().count()

    def get_orders_count(self, obj):
        if not obj:
            return 0

        return obj.company.provider_orders.all().count()


@six.add_metaclass(MetaFields)
class ApiBaseSerializer(ApiFullRelatedFieldsMixin,
                        ApiFieldsMixin,
                        serializers.ModelSerializer):

    # Small hack to use serializer with abstract model
    def get_fields(self):
        model = self.Meta.model
        model._meta.abstract = False

        try:
            return super(ApiBaseSerializer, self).get_fields()
        finally:
            model._meta.abstract = True


class WorkflowNodeSerializer(ApiBaseModelSerializer):
    class Meta:
        model = core_models.WorkflowNode
        fields = (
            '__all__', {
                'workflow': ('id', '__str__', 'name', 'model')
            }
        )

    def validate(self, data):
        core_models.WorkflowNode.validate_node(
            data["number"], data["workflow"], data["company"], data["active"],
            data.get("rules"), self.instance is None,
            self.instance and self.instance.id
        )
        return data


class WorkflowObjectSerializer(core_mixins.CreatedUpdatedByMixin, ApiBaseModelSerializer):
    method_fields = ('state_name', )

    class Meta:
        model = core_models.WorkflowObject
        fields = ('__all__', {
            'state': ('__all__', {
                'workflow': ('id', 'name'),
            })
        })

    def validate(self, data):
        core_models.WorkflowObject.validate_object(
            data["state"], data["object_id"], self.instance is None
        )
        return data

    def get_state_name(self, obj):
        if not obj:
            return None

        return obj.state.name_after_activation or obj.state.name_before_activation


class WorkflowTimelineSerializer(ApiBaseModelSerializer):

    method_fields = ('state', 'requirements', 'wf_object_id')

    class Meta:
        model = core_models.WorkflowNode
        fields = ('id', 'name_before_activation', 'name_after_activation', 'endpoint')

    def __init__(self, *args, **kwargs):
        self.target = kwargs.pop('target', None)

        super(WorkflowTimelineSerializer, self).__init__(*args, **kwargs)

    def get_state(self, obj):
        if not obj:
            return NOT_ALLOWED

        workflow_object = core_models.WorkflowObject.objects.filter(
            state=obj, object_id=self.target.id
        )
        if workflow_object.exists():
            workflow_object = workflow_object.latest('updated_at')
        else:
            workflow_object = None

        if workflow_object is not None:
            if workflow_object.active:
                return ACTIVE
            else:
                return VISITED
        else:
            if self.target.is_allowed(obj):
                return ALLOWED

            if not self.target._check_condition(obj.rules.get('required_states')):
                return NOT_ALLOWED
            return NEED_REQUIREMENTS

        return workflow_object is not None

    def get_requirements(self, obj):
        if not obj:
            return None

        if not self.target.is_allowed(obj):
            return self.target.get_required_messages(obj, False)

        return None

    def get_wf_object_id(self, obj):
        if not obj:
            return None

        workflow_object = core_models.WorkflowObject.objects.filter(
            state=obj, object_id=self.target.id
        ).first()

        return workflow_object and workflow_object.id


class NavigationSerializer(ApiBaseModelSerializer):

    method_fields = ('childrens', )

    class Meta:
        model = core_models.ExtranetNavigation
        fields = ('name', 'url', 'endpoint')

    def get_childrens(self, obj):
        if obj is None:
            return []

        childrens = obj.get_children()

        serializer = NavigationSerializer(childrens, many=True)
        return serializer.data


class DashboardModuleSerializer(ApiBaseModelSerializer):

    module_data = serializers.SerializerMethodField(read_only=True)

    def get_module_data(self, obj):
        model_cls = obj.content_type.model_class()
        return {
            'app': obj.content_type.app_label,
            'model': obj.content_type.model,
            'name': model_cls._meta.verbose_name,
            'plural_name': model_cls._meta.verbose_name_plural,
        }

    def validate(self, attrs):
        if core_models.DashboardModule.objects.filter(content_type=attrs['content_type']).exists():
            raise serializers.ValidationError(
                {'content_type': _("Module already exists")})
        return attrs

    class Meta:
        model = core_models.DashboardModule
        fields = ('id', 'content_type', 'module_data', 'is_active')


class UserDashboardModuleSerializer(ApiBaseModelSerializer):

    def validate(self, attrs):
        if core_models.UserDashboardModule.objects.filter(
                company_contact__contact__user=self.context['request'].user.id,
                dashboard_module=attrs['dashboard_module']).exists():
            raise serializers.ValidationError(
                {'dashboard_module': _("Module already exists")})
        return attrs

    class Meta:
        model = core_models.UserDashboardModule
        fields = ('id', 'company_contact',
                  'dashboard_module', 'position', 'ui_config')
        extra_kwargs = {
            'company_contact': {'read_only': True}
        }


class InvoiceRuleSerializer(ApiBaseModelSerializer):

    class Meta:
        model = core_models.InvoiceRule
        fields = ('__all__', )
        extra_kwargs = {
            'serial_number': {'required': False},
        }


class CompanyListSerializer(core_mixins.WorkflowStatesColumnMixin, ApiBaseModelSerializer):
    method_fields = (
        'primary_contact', 'terms_of_pay', 'regular_company_rel', 'master_company', 'state', 'city', 'credit_approved'
    )

    invoice_rule = InvoiceRuleSerializer(required=False)

    class Meta:
        model = core_models.Company
        fields = (
            '__all__',
            {
                'invoice_rule': '__all__',
                'manager': (
                    'id', '__str__',
                ),
                'groups': ('id', '__str__')
            }
        )
        extra_kwargs = {
            'company_settings': {'read_only': True},
            'myob_settings': {'read_only': True},
            'subcontractor': {'read_only': True},
            'groups': {'read_only': True},
        }

    def get_company_rel(self, company):
        company_rel = cache.get('company_rel_{}'.format(company.id), None)
        if not company_rel:
            current_site = get_current_site(self.context.get('request'))

            site_company = core_models.SiteCompany.objects.filter(
                site=current_site,
                company__master_companies__regular_company=company
            ).last()
            master_type = core_models.Company.COMPANY_TYPES.master
            if not site_company or site_company.company.type != master_type:
                return

            company_rel = company.regular_companies.filter(
                master_company=site_company.company
            ).last()

            cache.set('company_rel_{}'.format(company.id), company_rel)
        return company_rel

    def get_primary_contact(self, obj):
        if not obj:
            return

        company_rel = self.get_company_rel(obj)
        if not company_rel:
            return

        if company_rel and company_rel.primary_contact:
            return core_field.ApiBaseRelatedField.to_read_only_data(company_rel.primary_contact)

    def get_master_company(self, obj):
        if not obj:
            return

        company_rel = self.get_company_rel(obj)
        if not company_rel:
            return

        if company_rel:
            return core_field.ApiBaseRelatedField.to_read_only_data(company_rel.master_company)

    def get_active_states(self, obj):
        if obj:
            obj = self.get_company_rel(obj)

        return super().get_active_states(obj)

    def get_terms_of_pay(self, obj):
        if not obj:
            return

        return obj.get_terms_of_payment()

    def get_regular_company_rel(self, obj):
        relation = obj.regular_companies.all().last()
        return relation and core_field.ApiBaseRelatedField.to_read_only_data(relation)

    def get_address(self, obj):
        return obj.company_addresses.filter(hq=True).first()

    def get_state(self, obj):
        address = self.get_address(obj)

        if address:
            return address.address.state and address.address.state.name

    def get_city(self, obj):
        address = self.get_address(obj)

        if address:
            return address.address.city and address.address.city.name

    def get_credit_approved(self, obj):
        if obj.credit_check == core_models.Company.CREDIT_CHECK_CHOICES.approved:
            msg = _('Approved')
            if obj.credit_check_date:
                msg = '%s %s' % (msg, date_format(obj.credit_check_date, settings.DATE_FORMAT))
        else:
            msg = _('Not Approved')
        return msg


class FormStorageSerializer(ApiBaseModelSerializer):

    class Meta:
        fields = (
            'id', 'form', 'data', 'company', 'created_at', 'status'
        )
        model = core_models.FormStorage
        extra_kwargs = {
            'company': {'required': True},
            'status': {'read_only': True}
        }


class FormFieldSerializer(ApiBaseModelSerializer):

    def to_representation(self, instance):
        if not isinstance(instance, core_models.FormField):
            raise NotImplementedError

        class DynamicFormFieldSerializer(ApiBaseModelSerializer):

            method_fields = ('field_type', )

            class Meta:
                model = type(instance)
                fields = model.get_serializer_fields()

            def get_field_type(self, obj):
                return obj.get_field_type()

        return DynamicFormFieldSerializer(instance).data

    class Meta:
        model = core_models.FormField
        fields = '__all__'


class FormSerializer(ApiBaseModelSerializer):

    method_fields = ('model_fields', 'groups', 'company_links')

    class Meta:
        model = core_models.Form
        fields = (
            'id', 'title', 'company', 'builder', 'is_active',
            'short_description', 'save_button_text', 'submit_message'
        )

    def validate(self, attrs):
        """
        Validate data for permissions to change default forms without company.
        """
        request = self.context['request']
        if attrs['company'] is None and not request.user.is_superuser:
            raise serializers.ValidationError({
                'company': _("You can't update/create default forms")
            })
        if self.instance is not None and self.instance.company is None and \
                not request.user.is_superuser:
            raise serializers.ValidationError({
                'company': _("You can't update/create default forms")
            })

        # TODO: check unique together constraint
        # # check if company/builder relation already exists
        # qs = core_models.Form.objects.filter(company=attrs['company'],
        #                                 builder=attrs['builder'])
        # if qs.exists():
        #     if self.instance is None or qs.exclude(id=self.instance.id).exists():
        #         raise serializers.ValidationError({
        #             'company': _("Form for this company already exists"),
        #             'builder': _("Form for this builder already exists")
        #         })
        return attrs

    def get_model_fields(self, obj):
        if obj.builder:
            return core_models.ModelFormField.get_model_fields(
                obj.builder.content_type.model_class()
            )
        return []

    def get_groups(self, obj):
        return FormFieldGroupSerializer(obj.groups.all(), many=True).data

    def get_company_links(self, obj):
        return obj.get_company_links(self.context['request'].user.contact)


class FormFieldGroupSerializer(ApiBaseModelSerializer):

    method_fields = ('field_list', )

    class Meta:
        model = core_models.FormFieldGroup
        fields = (
            'id', 'form', 'name', 'position'
        )

    def get_field_list(self, obj):
        return FormFieldSerializer(instance=obj.fields.all(), many=True).data


class BaseFormFieldSerializer(ApiBaseModelSerializer):

    method_fields = ('field_type',)

    def get_field_type(self, obj):
        return obj.get_field_type()


class ModelFormFieldSerializer(BaseFormFieldSerializer):

    def validate(self, attrs):
        """
        Validate unique field on the form and check field name
        """
        if not attrs['group'].form.is_valid_model_field_name(attrs['name']):
            raise serializers.ValidationError({
                'name': _("Incorrect field name for model")
            })
        base_qs = core_models.FormField.objects.filter(
            group__form_id=attrs['group'].form_id, name=attrs['name']
        )
        if self.instance is not None:
            if base_qs.exclude(id=self.instance.id).exists():
                raise serializers.ValidationError({
                    'name': _('Field must be unique on the form')
                })
        else:
            if base_qs.exists():
                raise serializers.ValidationError({
                    'name': _('Field must be unique on the form')
                })
        return attrs

    class Meta:
        model = core_models.ModelFormField
        fields = (
            'id', 'group', 'name', 'label', 'placeholder', 'class_name',
            'required', 'position', 'help_text'
        )


class SelectFormFieldSerializer(BaseFormFieldSerializer):

    class Meta:
        model = core_models.SelectFormField
        fields = (
            'id', 'group', 'name', 'label', 'placeholder', 'class_name',
            'required', 'position', 'help_text', 'is_multiple', 'choices'
        )


class DateFormFieldSerializer(BaseFormFieldSerializer):

    class Meta:
        model = core_models.DateFormField
        fields = (
            'id', 'group', 'name', 'label', 'placeholder', 'class_name',
            'required', 'position', 'help_text'
        )


class CheckBoxFormFieldSerializer(BaseFormFieldSerializer):

    class Meta:
        model = core_models.CheckBoxFormField
        fields = (
            'id', 'group', 'name', 'label', 'placeholder', 'class_name',
            'required', 'position', 'help_text'
        )


class RadioButtonsFormFieldSerializer(BaseFormFieldSerializer):

    class Meta:
        model = core_models.RadioButtonsFormField
        fields = (
            'id', 'group', 'name', 'label', 'placeholder', 'class_name',
            'required', 'position', 'help_text', 'choices'
        )


class FileFormFieldSerializer(BaseFormFieldSerializer):

    class Meta:
        model = core_models.FileFormField
        fields = (
            'id', 'group', 'name', 'label', 'placeholder', 'class_name',
            'required', 'position', 'help_text'
        )


class ImageFormFieldSerializer(BaseFormFieldSerializer):

    class Meta:
        model = core_models.ImageFormField
        fields = (
            'id', 'group', 'name', 'label', 'placeholder', 'class_name',
            'required', 'position', 'help_text'
        )


class NumberFormFieldSerializer(BaseFormFieldSerializer):

    class Meta:
        model = core_models.NumberFormField
        fields = (
            'id', 'group', 'name', 'label', 'placeholder', 'class_name',
            'required', 'position', 'help_text',
            'min_value', 'max_value', 'step'
        )


class TextFormFieldSerializer(BaseFormFieldSerializer):

    class Meta:
        model = core_models.TextFormField
        fields = (
            'id', 'group', 'name', 'label', 'placeholder', 'class_name',
            'required', 'position', 'help_text',
            'max_length', 'subtype'
        )


class TextAreaFormFieldSerializer(BaseFormFieldSerializer):

    class Meta:
        model = core_models.TextAreaFormField
        fields = (
            'id', 'group', 'name', 'label', 'placeholder', 'class_name',
            'required', 'position', 'help_text',
            'max_length', 'rows'
        )


class FormBuilderSerializer(ApiBaseModelSerializer):

    class Meta:
        model = core_models.FormBuilder
        fields = (
            'id', 'content_type'
        )


class FormStorageApproveSerializer(ApiBaseModelSerializer):

    class Meta:
        model = core_models.FormStorage
        fields = ('status',)


class InvoiceLineSerializer(ApiBaseModelSerializer):

    class Meta:
        model = core_models.InvoiceLine
        fields = ('__all__', {
            'vat': ('id', 'name'),
            'timesheet': ('id', {
                'job_offer': ('id', 'candidate_contact'),
            })
        })


class TrialSerializer(serializers.Serializer):

    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    phone_mobile = serializers.CharField()
    company_name = serializers.CharField(max_length=127)
    website = serializers.CharField()

    def validate(self, data):
        email = data['email']
        company_name = data['company_name']
        website = data['website']
        phone_mobile = phonenumber.to_python(data['phone_mobile'])

        if not phone_mobile or not phone_mobile.is_valid():
            raise serializers.ValidationError({'phone_mobile': _('Invalid phone number')})

        try:
            if '@' not in email:
                raise serializers.ValidationError({'email': _('Invalid email')})
            validate_email(email)
        except ValidationError:
            raise serializers.ValidationError({'email': _('Invalid email')})

        try:
            core_models.Contact.objects.get(models.Q(email=email) | models.Q(phone_mobile=phone_mobile))
            key = 'email' if email else 'phone_mobile'
            raise serializers.ValidationError({
                key: _('User with this email or phone number already registered')
            })
        except core_models.Contact.DoesNotExist:
            pass

        try:
            core_models.Company.objects.get(models.Q(name=company_name) | models.Q(website=website))
            key = 'company_name' if company_name else 'website'
            raise serializers.ValidationError({
                key: _('Company with this name or website already registered')
            })
        except core_models.Company.DoesNotExist:
            pass

        return data
