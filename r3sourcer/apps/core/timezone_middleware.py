from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject
from rest_framework.request import Request

from r3sourcer.apps.core.api.authentication import JWTAuthentication


def get_user_jwt(request):
    """
    Replacement for django session auth get_user & auth.get_user
     JSON Web Token authentication. Inspects the token for the user_id,
     attempts to get that user from the DB & assigns the user on the
     request object. Otherwise it defaults to AnonymousUser.

    This will work with existing decorators like LoginRequired  ;)

    Returns: instance of user object or AnonymousUser object
    """
    user = None
    try:
        user_jwt = JWTAuthentication().authenticate(Request(request))
        if user_jwt is not None:
            # store the first part from the tuple (user, obj)
            user = user_jwt[0]
    except:
        pass

    return user or AnonymousUser()


class TimezoneMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.path.startswith('/admin'):
            request.user = SimpleLazyObject(lambda: get_user_jwt(request))
            if request.user != AnonymousUser():
                if request.user:
                    tzname = request.user.company.company_timezone
                    if tzname:
                        try:
                            timezone.activate(tzname)
                            print('Time zone "%s" activated' % str(tzname))
                        except Exception as e:
                            print('Unable to set timezone: %s' % str(e))
