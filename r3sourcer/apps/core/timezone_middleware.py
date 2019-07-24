from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class TimezoneMiddleware(MiddlewareMixin):
    def process_request(self, request):
        tzname = request.session.get('user_timezone')
        if tzname:
            try:
                timezone.activate(tzname)
                print('Time zone "%s" activated' % str(tzname))
            except Exception as e:
                print('Unable to set timezone: %s' % str(e))
