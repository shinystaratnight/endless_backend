import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, logout
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.views.mixins import OAuthLibMixin
from oauth2_provider.settings import oauth2_settings
from oauth2_provider_jwt.views import TokenView, WrongUsername
from oauth2_provider.models import get_access_token_model
from oauthlib.oauth2.rfc6749.tokens import BearerToken
from oauthlib.common import Request
from rest_framework import viewsets, status, exceptions, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from r3sourcer.apps.core.models import Contact, User, SiteCompany
from r3sourcer.apps.core.api.viewsets import BaseViewsetMixin
from r3sourcer.apps.core.utils.companies import get_site_master_company
from r3sourcer.apps.core.utils.utils import get_host
from r3sourcer.apps.core.views import OAuth2JWTTokenMixin

from ..models import TokenLogin
from ..tasks import send_login_message

from .serializers import LoginSerializer, ContactLoginSerializer, TokenLoginSerializer


@method_decorator(csrf_exempt, name='dispatch')
class AuthViewSet(OAuthLibMixin, OAuth2JWTTokenMixin, BaseViewsetMixin, viewsets.GenericViewSet):

    lookup_field = 'auth_token'
    queryset = TokenLogin.objects.all()
    permission_classes = (permissions.AllowAny, )
    serializer_class = LoginSerializer
    auth_backend = 'r3sourcer.apps.core.backends.ContactBackend'
    server_class = oauth2_settings.OAUTH2_SERVER_CLASS
    validator_class = oauth2_settings.OAUTH2_VALIDATOR_CLASS
    oauthlib_backend_class = oauth2_settings.OAUTH2_BACKEND_CLASS

    errors = {
        'logged_in': _('Please log out first.'),
        'email_not_found': _('Email or Password is not valid'),
        'phone_not_found': _('Phone number or Password is not valid'),
        'wrong_domain': _("You don't have access to current site"),
    }

    def get_object(self):
        obj = super(AuthViewSet, self).get_object()

        if obj.loggedin_at is not None:
            raise exceptions.AuthenticationFailed()
        return obj

    def list(self, request, *args, **kwargs):
        self.http_method_not_allowed(request, *args, **kwargs)

    def is_login_allowed(self, request, user):
        contact = user.contact
        closest_company = None

        if contact.is_company_contact():
            site_master_company = get_site_master_company(request)
            company_contacts = contact.company_contact.filter(
                Q(relationships__company=site_master_company) |
                Q(relationships__company__regular_companies__master_company=site_master_company),
                relationships__active=True
            )

            if company_contacts.exists():
                closest_company = site_master_company

        if not closest_company:
            closest_company = user.contact.get_closest_company()

        host = get_host(request)

        try:
            redirect_site = SiteCompany.objects.get(company=closest_company).site
        except SiteCompany.DoesNotExist:
            raise exceptions.PermissionDenied(self.errors['wrong_domain'])

        if not user.is_superuser and redirect_site.domain != host:
            if host != settings.REDIRECT_DOMAIN:
                raise exceptions.PermissionDenied(self.errors['wrong_domain'])
            else:
                host_url = 'http://{}'.format(redirect_site.domain)
                cache.set('user_site_%s' % str(user.id), redirect_site.domain)
                return False, host_url
        else:
            cache.set('user_site_%s' % str(user.id), host)
            return True, None

        return False, None

    def get_jwt_oauth2_token(self, request, token_content, status, host=None, username=None):
        if TokenView._is_jwt_config_set():
            try:
                token_content['access_token_jwt'] = self._get_access_token_jwt(
                    request, token_content, host, username=username
                )
                return token_content, status
            except WrongUsername:
                content = {
                    "error": "invalid_request",
                    "error_description": "Request username doesn't match username in original authorize",
                }
                return content, 400

    @action(methods=['post'], detail=False)
    def login(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_email = '@' in serializer.data['username']

        contact = Contact.objects.filter(
            Q(email=serializer.data['username']) |
            Q(phone_mobile=serializer.data['username'])
        ).first()
        if contact and ('password' not in serializer.data or
                        not serializer.data['password']):
            send_login_message(serializer.data['username'], contact)
            if is_email:
                message = _('E-mail with login token was sent.')
            else:
                message = _('SMS with login token was sent.')

            return Response({
                'status': 'success',
                'message': message,
            }, status=status.HTTP_200_OK)

        user = authenticate(username=serializer.data['username'],
                            password=serializer.data.get('password'))
        if user is None:
            if contact is not None:
                if is_email:
                    message = {
                        'username': self.errors['email_not_found'],
                    }
                else:
                    message = {
                        'username': self.errors['phone_not_found'],
                    }
            else:
                message = {
                    'username': self.errors['email_not_found'] if is_email else self.errors['phone_not_found'],
                }

            raise exceptions.ValidationError(message)

        is_login, redirect_host = self.is_login_allowed(request, user)

        if not serializer.data['remember_me']:
            request.session.set_expiry(0)

        url, headers, body, resp_status = self.create_token_response(request)
        token_content, resp_status = self.get_jwt_oauth2_token(request, json.loads(body), resp_status, redirect_host)

        response_data = {
            'status': 'success',
            'data': {
                'contact': ContactLoginSerializer(contact).data,
                **token_content,
            }
        }

        if redirect_host is not None:
            response_data['data']['redirect'] = redirect_host

        return Response(response_data, status=resp_status)

    def _generate_token(self, request, user):
        request_validator = self.get_validator_class()()
        core = self.get_oauthlib_core()
        uri, http_method, body, headers = core._extract_params(request)

        token_request = Request(uri, http_method, body, headers)
        bearer_token = BearerToken(request_validator)
        token = bearer_token.create_token(token_request, save_token=False)

        expires = timezone.now() + timedelta(seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS)
        client = None
        AccessToken = get_access_token_model()
        access_token = AccessToken(
            user=user,
            scope='write read',
            expires=expires,
            token=token["access_token"],
            application=client
        )
        access_token.save()

        token['expires_in'] = oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS

        return token

    @action(methods=['get'], detail=True)
    def login_by_token(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = TokenLoginSerializer(instance)

        user = instance.contact.user
        if user is None:
            raise exceptions.NotFound()

        instance.loggedin_at = timezone.now()
        instance.save()

        cache.set('user_site_%s' % str(user.id), request.META.get('HTTP_HOST'))

        request.session.set_expiry(0)

        token_body = self._generate_token(request, user)
        token_content, resp_status = self.get_jwt_oauth2_token(
            request, token_body, 200, username=user.contact.email or user.contact.phone_mobile
        )

        data = {
            'status': 'success',
            'data': serializer.data,
            **token_content,
        }

        return Response(data)

    @action(methods=['get'], detail=False)
    def restore_session(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise exceptions.AuthenticationFailed()
        serializer = ContactLoginSerializer(request.user.contact)
        cache.set('user_site_%s' % str(request.user.id), request.META.get('HTTP_HOST'))
        return Response({
            'status': 'success',
            'data': {
                'contact': serializer.data,
                'user': str(request.user.id)
            }
        }, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False)
    def logout(self, request, *args, **kwargs):
        logout(request)

        return Response({
            'status': 'success',
            'message': _('You are logged out')
        }, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=True)
    def loginas(self, request, auth_token, *args, **kwargs):
        if not request.user.is_authenticated:
            raise exceptions.ValidationError(_('Please login first'))

        try:
            user = User.objects.get(id=auth_token)
        except User.DoesNotExist:
            raise exceptions.NotFound({'user': _('User not found')})

        is_login, redirect_host = self.is_login_allowed(request, user)

        token_body = self._generate_token(request, user)
        token_content, resp_status = self.get_jwt_oauth2_token(
            request, token_body, 200, redirect_host, username=user.contact.email or user.contact.phone_mobile
        )

        response_data = {
            'status': 'success',
            'message': _('You are logged in as {user}').format(user=str(user.contact)),
            **token_content,
        }

        return Response(response_data, status=status.HTTP_200_OK)
