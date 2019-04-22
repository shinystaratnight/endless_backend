from rest_framework import serializers

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.translation import ugettext_lazy as _

from phonenumber_field import phonenumber

from r3sourcer.apps.core.api.serializers import ApiBaseModelSerializer, ApiContactImageFieldsMixin
from r3sourcer.apps.core.models import Contact

from .. import models


class LoginSerializer(serializers.Serializer):

    username = serializers.CharField(
        max_length=255,
        required=True,
        label=_('Phone or E-mail address')
    )
    password = serializers.CharField(
        max_length=128,
        required=False,
        allow_blank=True,
        allow_null=True,
        label=_('Password (optional)')
    )
    remember_me = serializers.BooleanField(
        required=False,
        default=False,
        label=_('Remember me')
    )

    class Meta:
        model = models.TokenLogin
        fields = ('username', 'password', 'remember_me')

    def validate(self, data):
        username = data['username']

        phone_number = phonenumber.to_python(username)
        if not phone_number or not phone_number.is_valid():
            try:
                if '@' not in username:
                    raise ValidationError(_('invalid email'))
                validate_email(username)
            except ValidationError:
                raise serializers.ValidationError(
                    _(
                        "Please enter a correct email or mobile phone number and password. "
                        "Note that both fields may be case-sensitive."
                    ),
                    code='invalid_login',
                )

        return data


class TokenLoginSerializer(ApiBaseModelSerializer):
    class Meta:
        model = models.TokenLogin
        fields = ('contact', 'redirect_to', 'role')


class ContactLoginSerializer(ApiContactImageFieldsMixin, ApiBaseModelSerializer):
    name = serializers.SerializerMethodField()
    contact_type = serializers.CharField(source='get_role', read_only=True)
    contact_id = serializers.UUIDField(source='get_role_id', read_only=True)

    image_fields = ('picture', )
    method_fields = ('company', 'company_id', 'candidate_contact')

    class Meta:
        model = Contact
        fields = ('id', 'name', 'contact_type', 'contact_id', 'picture', 'email')

    def get_name(self, obj):
        return str(obj)

    def get_company(self, obj):
        return obj.get_closest_company().name

    def get_company_id(self, obj):
        return str(obj.get_closest_company().id)

    def get_candidate_contact(self, obj):
        if obj.is_candidate_contact():
            return str(obj.candidate_contacts.pk)
