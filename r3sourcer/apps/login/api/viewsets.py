from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from loginas.utils import login_as
from rest_framework import viewsets, status, exceptions, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from r3sourcer.apps.core.models import Contact, User
from r3sourcer.apps.core.api.viewsets import BaseViewsetMixin

from ..models import TokenLogin
from ..tasks import send_login_message

from .serializers import LoginSerializer, ContactLoginSerializer


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
    }

    def get_object(self):
        obj = super(AuthViewSet, self).get_object()

        if obj.loggedin_at is not None:
            raise exceptions.AuthenticationFailed()
        return obj

    def list(self, request, *args, **kwargs):
        self.http_method_not_allowed(request, *args, **kwargs)

    @action(methods=['post'], detail=False)
    def login(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            raise exceptions.PermissionDenied(self.errors['logged_in'])

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
                    'register': 'email' if is_email else 'phone_mobile',
                }

            raise exceptions.ValidationError(message)

        login(request, user)
        cache.set('user_site_%s' % str(user.id), request.META.get('HTTP_HOST'))

        if not serializer.data['remember_me']:
            request.session.set_expiry(0)

        return Response({
            'status': 'success',
            'data': {
                'contact': ContactLoginSerializer(contact).data
            }
        }, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=True)
    def login_by_token(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

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
        if not request.user.is_authenticated():
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

        logout(request)

        login_as(user, request, store_original_user=False)

        return Response({
            'status': 'success',
            'message': _('You are logged in as {user}').format(user=str(user.contact))
        }, status=status.HTTP_200_OK)
