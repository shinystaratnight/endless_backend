import decimal

from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404
from rest_framework import exceptions
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from r3sourcer.apps.company_settings import serializers
from r3sourcer.apps.company_settings.models import MYOBAccount, GlobalPermission
from r3sourcer.apps.core.models import User
from r3sourcer.apps.myob.api.wrapper import MYOBAuth, MYOBClient
from r3sourcer.apps.myob.serializers import MYOBCompanyFileSerializer
from r3sourcer.apps.myob.models import MYOBCompanyFile, MYOBCompanyFileToken, MYOBAuthData


class GlobalPermissionListView(ListAPIView):
    """
    Returns list of all GlobalPermissions.
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
    Returns list of all GlobalPermissions of a given Group.
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
    Returns list of all GlobalPermissions of a given User.
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
    Sets GlobalPermission to a given Group.
    """
    def post(self, request, id, *args, **kwargs):
        group = get_object_or_404(Group, id=id)
        permission_id_list = list(map(int, request.data.get('permission_list', None)))
        permission_list = list(GlobalPermission.objects.filter(id__in=permission_id_list))
        group.permissions.add(*permission_list)
        return Response()


class SetUserGlobalPermissionView(APIView):
    """
    Sets GlobalPermission to a given User.
    """
    def post(self, request, id, *args, **kwargs):
        user = get_object_or_404(User, id=id)
        permission_id_list = request.data.get('permission_list', None)
        permission_list = list(GlobalPermission.objects.filter(id__in=permission_id_list))
        user.user_permissions.add(*permission_list)
        return Response()


class RevokeGroupGlobalPermissionView(APIView):
    """
    Revokes GlobalPermission of a given Group.
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
    Revokes GlobalPermission of a given User.
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
    Creates a Group and connects it with a Company.
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
    Returns list of Groups of a given Company.
    """
    serializer_class = serializers.GroupSerializer

    def get_queryset(self):
        company = self.request.user.contact.company_contact.first().companies.first()

        if not company:
            raise exceptions.APIException("User has no relation to any company.")

        return company.groups.all()


class CompanyGroupDeleteView(APIView):
    """
    Deletes a Group.
    """
    def get(self, request, id, *args, **kwargs):
        group = get_object_or_404(Group, id=id)
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AddUserToGroupView(APIView):
    """
    Adds User to a Group.
    """
    def post(self, request, id, *args, **kwargs):
        user_id = request.data.get('user_id')
        user = get_object_or_404(User, id=user_id)
        group = get_object_or_404(Group, id=id)
        group.user_set.add(user)
        return Response()


class RemoveUserFromGroupView(APIView):
    """
    Removes User from a Group.
    """
    def post(self, request, id, *args, **kwargs):
        user_id = request.data.get('user_id')
        user = get_object_or_404(User, id=user_id)
        group = get_object_or_404(Group, id=id)
        group.user_set.remove(user)
        return Response()


class UserGroupListView(ListAPIView):
    """
    Returns list of Groups of a given User.
    """
    serializer_class = serializers.UserGroupSerializer

    def get_queryset(self):
        user = get_object_or_404(User, id=self.kwargs['id'])
        return user.groups.all()


class CompanyUserListView(APIView):
    """
    Returns list of all users of current user's company.
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


class CompanySettingsView(APIView):
    def get(self, *args, **kwargs):
        company = self.request.user.company

        if not company:
            raise exceptions.APIException("User has no relation to any company.")

        company_settings = company.company_settings
        invoice_rule = company.invoice_rules.first()
        payslip_rule = company.payslip_rules.first()
        # account_set = company.company_settings.account_set

        company_settings_serializer = serializers.CompanySettingsSerializer(company_settings)
        invoice_rule_serializer = serializers.InvoiceRuleSerializer(invoice_rule)
        payslip_rule_serializer = serializers.PayslipRuleSerializer(payslip_rule)
        # account_set_serializer = serializers.AccountSetSerializer(account_set)

        data = {
            "company_settings": company_settings_serializer.data,
            "invoice_rule": invoice_rule_serializer.data,
            "payslip_rule": payslip_rule_serializer.data,
            # "account_set": account_set_serializer.data
        }

        return Response(data)

    def post(self, *args, **kwargs):
        company = self.request.user.contact.company_contact.first().companies.first()

        if not company:
            raise exceptions.APIException("User has no relation to any company.")

        if 'company_settings' in self.request.data:
            serializer = serializers.CompanySettingsSerializer(company.company_settings,
                                                               data=self.request.data['company_settings'],
                                                               partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        if 'invoice_rule' in self.request.data:
            serializer = serializers.InvoiceRuleSerializer(company.invoice_rules.first(),
                                                           data=self.request.data['invoice_rule'],
                                                           partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        if 'payslip_rule' in self.request.data:
            serializer = serializers.PayslipRuleSerializer(company.payslip_rules.first(),
                                                           data=self.request.data['payslip_rule'],
                                                           partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        if 'account_set' in self.request.data:
            serializer = serializers.MYOBSettingsSerializer(company.company_settings.account_set,
                                                          data=self.request.data['account_set'],
                                                          partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response()


class CompanyFileAccountsView(APIView):
    def get(self, request, *args, **kwargs):
        company_file = get_object_or_404(MYOBCompanyFile, id=self.kwargs['id'])
        myob_accounts = company_file.accounts.all()
        serializer = serializers.MYOBAccountSerializer(myob_accounts, many=True)
        data = {
            'myob_accounts': serializer.data
        }

        return Response(data)


class MYOBAuthorizationView(APIView):
    """
    Accepts Developer Key and Developer Secret and checks if they are correct.
    """
    def post(self, request, *args, **kwargs):
        data = {
            'client_id': request.data.get('api_key', None),
            'client_secret': request.data.get('api_secret', None),
            'scope': 'CompanyFile',
            'code': request.data.get('code', None),
            'redirect_uri': request.data.get('redirect_uri', None),
            'grant_type': 'authorization_code'
        }
        auth_client = MYOBAuth(self.request)
        response = auth_client.retrieve_access_token(data=data)
        MYOBAuthData.objects.get_or_create(
            client_id=request.data.get('api_key', None),
            client_secret=request.data.get('api_secret', None),
            access_token=response['access_token'],
            refresh_token=response['refresh_token'],
            myob_user_uid=response['user']['uid'],
            myob_user_username=response['user']['username'],
            expires_in=response['expires_in'],
            user=request.user
        )

        return Response()


class UserCompanyFilesView(APIView):
    """
    Returns all company files of current user.
    """
    def get(self, request, *args, **kwargs):
        serializer = MYOBCompanyFileSerializer(request.user.company_files, many=True)
        data = {
            'company_files': serializer.data
        }
        return Response(data)


class RefreshCompanyFilesView(APIView):
    """
    Fetches a list of company files from MYOB API, save and returns it.
    """
    def get(self, request, *args, **kwargs):
        auth_data = request.user.auth_data.latest('created')
        client = MYOBClient(auth_data=auth_data)
        raw_company_files = client.get_company_files()
        new_company_files = list()

        for raw_company_file in raw_company_files:
            company_file, created = MYOBCompanyFile.objects.update_or_create(cf_id=raw_company_file['Id'],
                                                                             defaults={
                                                                                 'cf_uri': raw_company_file['Uri'],
                                                                                 'cf_name': raw_company_file['Name']
                                                                             })
            company_file_token, _ = MYOBCompanyFileToken.objects.update_or_create(company_file=company_file,
                                                                                  company=request.user.company,
                                                                                  defaults={
                                                                                      'auth_data': auth_data,
                                                                                  })
            if created:
                new_company_files.append(company_file)

        serialzer = MYOBCompanyFileSerializer(new_company_files, many=True)
        data = {
            "company_files": serialzer.data
        }

        return Response(data)


class CheckCompanyFilesView(APIView):
    """
    Accepts credentials and company file id and check if they are valid.
    """
    def post(self, request, *args, **kwargs):
        username = self.request.data.get('username', None)
        password = self.request.data.get('password', None)
        company_file_id = self.request.data.get('id', None)
        company_file = MYOBCompanyFile.objects.get(cf_id=company_file_id)
        auth_data = request.user.auth_data.latest('created')
        client = MYOBClient(auth_data=auth_data)
        response = client.check_company_file(company_file_id, username, password)
        is_valid = response.status_code == 200
        company_file_token = company_file.tokens.filter(auth_data__user=request.user).latest('created')
        company_file_token.cf_token = client.encode_cf_token(username, password)
        company_file_token.save()
        company_file.authenticated = is_valid
        company_file.save()
        data = {
            "is_valid": is_valid
        }

        return Response(data)


class MYOBAccountSyncView(APIView):
    """
    Fetches all accounts of all user's company's company files from MYOB API and saves it into database
    """
    def get(self, request, *args, **kwargs):
        auth_data = request.user.auth_data.latest('created')
        client = MYOBClient(auth_data=auth_data)

        for company_file in request.user.company_files:
            if not company_file.authenticated:
                continue

            company_file_token = company_file.tokens.filter(auth_data__user=request.user).latest('created').cf_token
            accounts = client.get_accounts(company_file.cf_id, company_file_token).json()['Items']

            for account in accounts:
                MYOBAccount.objects.update_or_create(uid=account['UID'],
                    defaults={
                        'name': account['Name'],
                        'display_id': account['DisplayID'],
                        'classification': account['Classification'],
                        'type': account['Type'],
                        'number': account['Number'],
                        'description': account['Description'],
                        'is_active': account['IsActive'],
                        'level': account['Level'],
                        'opening_balance': account['OpeningBalance'],
                        'current_balance': account['CurrentBalance'],
                        'is_header': account['IsHeader'],
                        'uri': account['URI'],
                        'row_version': account['RowVersion'],
                        'company_file': company_file
                    }
                )

        data = {
            "response": accounts
        }

        # TODO: update last_refreshed
        return Response(data)


class MYOBSettingsView(APIView):
    def get(self, *args, **kwargs):
        company = self.request.user.company

        if not company:
            raise exceptions.APIException("User has no relation to any company.")

        account_set = company.company_settings.account_set
        account_set_serializer = serializers.MYOBSettingsSerializer(account_set)
        data = {
            "account_set": account_set_serializer.data
        }
        return Response(data)
