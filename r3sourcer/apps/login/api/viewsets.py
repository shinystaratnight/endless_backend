from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from loginas.utils import login_as
from rest_framework import viewsets, status, exceptions, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from r3sourcer.apps.core.models import Contact, User, SiteCompany
from r3sourcer.apps.core.api.viewsets import BaseViewsetMixin
from r3sourcer.apps.core.utils.companies import get_site_master_company

from ..models import TokenLogin
from ..tasks import send_login_message

from .serializers import LoginSerializer, ContactLoginSerializer, TokenLoginSerializer


class AuthViewSet(BaseViewsetMixin,
                  viewsets.GenericViewSet):

    lookup_field = 'auth_token'
    queryset = TokenLogin.objects.all()
    permission_classes = (permissions.AllowAny, )
    serializer_class = LoginSerializer
    auth_backend = 'r3sourcer.apps.core.backends.ContactBackend'

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

        host = request.get_host()
        redirect_host = None

        try:
            redirect_site = SiteCompany.objects.get(company=closest_company).site
        except SiteCompany.DoesNotExist:
            raise exceptions.PermissionDenied(self.errors['wrong_domain'])

        if not user.is_superuser and redirect_site.domain != host:
            if host != settings.REDIRECT_DOMAIN:
                raise exceptions.PermissionDenied(self.errors['wrong_domain'])
            else:
                host_url = 'http://{}'.format(redirect_site.domain)
                token_login = TokenLogin.objects.create(
                    contact=user.contact,
                    redirect_to='/'
                )
                redirect_host = '{}{}'.format(host_url, token_login.auth_url)
                cache.set('user_site_%s' % str(user.id), redirect_site.domain)
                return False, redirect_host
        else:
            cache.set('user_site_%s' % str(user.id), request.META.get('HTTP_HOST'))
            return True, None

        return False, None

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

        if is_login:
            login(request, user)

        if not serializer.data['remember_me']:
            request.session.set_expiry(0)

        response_data = {
            'status': 'success',
            'data': {
                'contact': ContactLoginSerializer(contact).data
            }
        }

        if redirect_host is not None:
            response_data['data']['redirect'] = redirect_host

        return Response(response_data, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=True)
    def login_by_token(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = TokenLoginSerializer(instance)

        user = instance.contact.user
        if user is None:
            raise exceptions.NotFound()

        if request.user != user:
            logout(request)

        if not request.user.is_authenticated:
            login(request, user, backend=self.auth_backend)

        instance.loggedin_at = timezone.now()
        instance.save()

        cache.set('user_site_%s' % str(user.id), request.META.get('HTTP_HOST'))

        request.session.set_expiry(0)

        return Response({'status': 'success', 'data': serializer.data})

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

        logout(request)

        if is_login:
            login_as(user, request, store_original_user=False)

        response_data = {
            'status': 'success',
            'message': _('You are logged in as {user}').format(user=str(user.contact))
        }

        if redirect_host is not None:
            response_data['redirect_to'] = redirect_host

        return Response(response_data, status=status.HTTP_200_OK)
