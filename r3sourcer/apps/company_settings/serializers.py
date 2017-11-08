from django.contrib.auth.models import Group
from rest_framework import serializers

from r3sourcer.apps.core.models import User
from r3sourcer.apps.company_settings.models import GlobalPermission


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
    name = serializers.ReadOnlyField(source='get_full_name')

    class Meta:
        model = User
        fields = ('id', 'name')


class UserGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for rendering list of Groups of a given User in UserGroupListView
    """
    class Meta:
        model = Group
        fields = ('id', 'name')
