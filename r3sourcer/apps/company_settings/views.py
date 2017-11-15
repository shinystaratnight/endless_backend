from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404
from rest_framework import exceptions
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from r3sourcer.apps.company_settings import serializers
from r3sourcer.apps.company_settings.models import GlobalPermission
from r3sourcer.apps.core.models import User


class GlobalPermissionListView(ListAPIView):
    """
    Returns list of all GlobalPermissions
    """
    def get(self, *args, **kwargs):
        permissions = GlobalPermission.objects.all()
        serializer = serializers.GlobalPermissionSerializer(permissions, many=True)
        data = {
            "permission_list": serializer.data
        }
        return Response(data)


class GroupGlobalPermissionListView(ListAPIView):
    """
    Returns list of all GlobalPermissions of a given Group
    """
    def get(self, *args, **kwargs):
        group = get_object_or_404(Group, id=self.kwargs['id'])
        permissions = GlobalPermission.objects.filter(group=group)
        serializer = serializers.GlobalPermissionSerializer(permissions, many=True)
        data = {
            "permission_list": serializer.data
        }
        return Response(data)


class UserGlobalPermissionListView(ListAPIView):
    """
    Returns list of all GlobalPermissions of a given User
    """
    def get(self, *args, **kwargs):
        user = get_object_or_404(User, id=self.kwargs['id'])
        permissions = GlobalPermission.objects.filter(user=user)
        serializer = serializers.GlobalPermissionSerializer(permissions, many=True)
        data = {
            "permission_list": serializer.data
        }
        return Response(data)


class SetGroupGlobalPermissionView(APIView):
    """
    Sets GlobalPermission to a given Group
    """
    def post(self, request, id, *args, **kwargs):
        group = get_object_or_404(Group, id=id)
        permission_id_list = list(map(int, request.data.get('permission_list', None)))
        permission_list = list(GlobalPermission.objects.filter(id__in=permission_id_list))
        group.permissions.add(*permission_list)
        return Response()


class SetUserGlobalPermissionView(APIView):
    """
    Sets GlobalPermission to a given User
    """
    def post(self, request, id, *args, **kwargs):
        user = get_object_or_404(User, id=id)
        permission_id_list = request.data.get('permission_list', None)
        permission_list = list(GlobalPermission.objects.filter(id__in=permission_id_list))
        user.user_permissions.add(*permission_list)
        return Response()


class RevokeGroupGlobalPermissionView(APIView):
    """
    Revokes GlobalPermission of a given Group
    """
    def post(self, request, id, *args, **kwargs):
        group = get_object_or_404(Group, id=id)
        serializer = serializers.PermissionListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        permission_list = list(GlobalPermission.objects.filter(id__in=data['permission_list']))
        group.permissions.remove(*permission_list)
        return Response()


class RevokeUserGlobalPermissionView(APIView):
    """
    Revokes GlobalPermission of a given User
    """
    def post(self, request, id, *args, **kwargs):
        user = get_object_or_404(User, id=id)
        serializer = serializers.PermissionListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        permission_list = list(GlobalPermission.objects.filter(id__in=data['permission_list']))
        user.user_permissions.remove(*permission_list)
        return Response()


class CompanyGroupCreateView(APIView):
    """
    Creates a Group and connects it with a Company
    """
    def post(self, request, *args, **kwargs):
        company = request.user.contact.company_contact.first().companies.first()

        if not company:
            raise exceptions.APIException("User has no relation to any company.")

        name = request.data.get('name')
        group = Group.objects.create(name=name)
        company.groups.add(group)
        return Response(status=status.HTTP_201_CREATED)


class CompanyGroupListView(ListAPIView):
    """
    Returns list of Groups of a given Company
    """
    serializer_class = serializers.GroupSerializer

    def get_queryset(self):
        company = self.request.user.contact.company_contact.first().companies.first()

        if not company:
            raise exceptions.APIException("User has no relation to any company.")

        return company.groups.all()


class CompanyGroupDeleteView(APIView):
    """
    Deletes a Group
    """
    def get(self, request, id, *args, **kwargs):
        group = get_object_or_404(Group, id=id)
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AddUserToGroupView(APIView):
    """
    Adds User to a Group
    """
    def post(self, request, id, *args, **kwargs):
        user_id = request.data.get('user_id')
        user = get_object_or_404(User, id=user_id)
        group = get_object_or_404(Group, id=id)
        group.user_set.add(user)
        return Response()


class RemoveUserFromGroupView(APIView):
    """
    Removes User from a Group
    """
    def post(self, request, id, *args, **kwargs):
        user_id = request.data.get('user_id')
        user = get_object_or_404(User, id=user_id)
        group = get_object_or_404(Group, id=id)
        group.user_set.remove(user)
        return Response()


class UserGroupListView(ListAPIView):
    """
    Returns list of Groups of a given User
    """
    serializer_class = serializers.UserGroupSerializer

    def get_queryset(self):
        user = get_object_or_404(User, id=self.kwargs['id'])
        return user.groups.all()


# TODO: move this view to another app; most likely it will be company_settings
class CompanyUserListView(APIView):
    """
    Returns list of all users of current user's company
    """
    def get(self, *args, **kwargs):
        company = self.request.user.contact.company_contact.first().companies.first()

        if not company:
            raise exceptions.APIException("User has no relation to any company.")

        user_list = User.objects.filter(contact__company_contact__relationships__company=company)
        serializer = serializers.CompanyUserSerializer(user_list, many=True)
        data = {
            "user_list": serializer.data
        }
        return Response(data)
