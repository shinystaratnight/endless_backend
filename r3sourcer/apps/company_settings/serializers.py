from django.contrib.auth.models import Group
from rest_framework import serializers

from r3sourcer.apps.company_settings.models import CompanySettings, AccountSet, MYOBAccount
from r3sourcer.apps.core.api.fields import ApiBase64ImageField
from r3sourcer.apps.core.models import InvoiceRule
from r3sourcer.apps.hr.models import PayslipRule
from r3sourcer.apps.core.models import User
from r3sourcer.apps.company_settings.models import GlobalPermission


class CompanySettingsSerializer(serializers.ModelSerializer):
    logo = ApiBase64ImageField()

    class Meta:
        model = CompanySettings
        fields = ('id', 'logo', 'color_scheme', 'font', 'forwarding_number')
        read_only_fields = ('company',)


class PayslipRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayslipRule
        fields = ('id', 'period')


class InvoiceRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceRule
        fields = ('id', 'period', 'separation_rule', 'show_candidate_name')


class MYOBAccountSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = MYOBAccount
        fields = ('id', 'number', 'name', 'type')


class AccountSetSerializer(serializers.ModelSerializer):
    subcontractor_contract_work = MYOBAccountSerializer()
    subcontractor_gst = MYOBAccountSerializer()
    candidate_wages = MYOBAccountSerializer()
    candidate_superannuation = MYOBAccountSerializer()
    company_client_labour_hire = MYOBAccountSerializer()
    company_client_gst = MYOBAccountSerializer()

    class Meta:
        model = AccountSet
        fields = ('subcontractor_contract_work', 'subcontractor_gst', 'candidate_wages', 'candidate_superannuation',
                  'company_client_labour_hire', 'company_client_gst')

    def update(self, instance, validated_data):
        fields = ('subcontractor_contract_work', 'subcontractor_gst', 'candidate_wages', 'candidate_superannuation',
                  'company_client_labour_hire', 'company_client_gst')

        for field in fields:
            if validated_data.get(field, None):
                myob_account = MYOBAccount.objects.filter(id=validated_data[field]['id']).first()

                if myob_account:
                    setattr(instance, field, myob_account)

        instance.save()
        return instance


class GlobalPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalPermission
        fields = ('id', 'name', 'codename')


class GroupSerializer(serializers.ModelSerializer):
    permissions = GlobalPermissionSerializer(source='permissions.all', many=True)

    class Meta:
        model = Group
        fields = ('id', 'name', 'permissions')


class PermissionListSerializer(serializers.Serializer):
    permission_list = serializers.ListField(child=serializers.IntegerField(), min_length=1)

    def validate_permission_list(self, permission_list):
        permission_count = GlobalPermission.objects.filter(id__in=permission_list).count()

        if permission_count != len(permission_list):
            raise serializers.ValidationError("Some permissions dont exist.")

        return permission_list


class CompanyUserSerializer(serializers.ModelSerializer):
    """
    Serializer for rendering list of Users of a given Company in CompanyUserListView
    """
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'name')

    def get_name(self, obj):
        return obj.contact.first_name + ' ' + obj.contact.last_name


class UserGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for rendering list of Groups of a given User in UserGroupListView
    """
    class Meta:
        model = Group
        fields = ('id', 'name')
