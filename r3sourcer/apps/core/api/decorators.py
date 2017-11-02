from rest_framework.response import Response


def metadata(self, request, *args, **kwargs):
    endpoint = kwargs.get('endpoint')
    if endpoint is None:
        endpoint = self.endpoint

    origin_serializer_class = endpoint.serializer
    origin_fieldsets = endpoint.fieldsets
    origin_list_display = endpoint.list_display
    serializer_calss = kwargs.get('serializer') or origin_serializer_class
    fieldsets = kwargs.get('fieldsets') or origin_fieldsets
    list_display = kwargs.get('list_display') or origin_list_display

    endpoint.serializer = serializer_calss
    endpoint.fieldsets = fieldsets
    endpoint.list_display = list_display

    origin_endpoint = self.endpoint
    self.endpoint = endpoint

    meta = self.metadata_class()
    data = meta.determine_metadata(request, self)

    endpoint.serializer = origin_serializer_class
    endpoint.fieldsets = origin_fieldsets
    endpoint.list_display = origin_list_display

    self.endpoint = origin_endpoint

    return Response(data)


def list_route(methods=None, serializer=None, fieldsets=None,
               endpoint=None, list_display=None, **kwargs):
    methods = ['get'] if (methods is None) else methods
    if 'options' not in methods:
        methods.extend(['options'])

    def decorator(func):
        def metadata_wrapper(self, request, *args, **kwargs):
            if request.method == 'OPTIONS':
                return metadata(
                    self, request, serializer=serializer,
                    fieldsets=fieldsets, endpoint=endpoint,
                    list_display=list_display, * args, **kwargs
                )

            return func(self, request, *args, **kwargs)

        metadata_wrapper.bind_to_methods = methods
        metadata_wrapper.detail = False
        metadata_wrapper.kwargs = kwargs
        return metadata_wrapper
    return decorator


def detail_route(methods=None, serializer=None, fieldsets=None,
                 endpoint=None, **kwargs):
    methods = ['get'] if (methods is None) else methods
    if 'options' not in methods:
        methods.extend(['options'])

    def decorator(func):
        def metadata_wrapper(self, request, *args, **kwargs):
            if request.method == 'OPTIONS':
                return metadata(
                    self, request, serializer=serializer,
                    fieldsets=fieldsets, endpoint=endpoint,
                    *args, **kwargs
                )

            return func(self, request, *args, **kwargs)

        metadata_wrapper.bind_to_methods = methods
        metadata_wrapper.detail = True
        metadata_wrapper.kwargs = kwargs
        return metadata_wrapper
    return decorator
