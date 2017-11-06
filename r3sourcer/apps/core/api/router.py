from django.conf import settings

from drf_auto_endpoint.router import EndpointRouter


class ApiRouter(EndpointRouter):

    def register(self, *args, **kwargs):
        if not settings.TEST:
            super().register(*args, **kwargs)
