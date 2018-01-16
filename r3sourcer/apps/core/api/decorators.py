from rest_framework.response import Response


def metadata(self, request, *args, **kwargs):
    endpoint = kwargs.get('endpoint')
    if endpoint is None:
        endpoint = self.endpoint

    backup_fields = ('serializer', 'fieldsets', 'list_display', 'list_editable')
    origin = {}

    for backup_field in backup_fields:
        origin[backup_field] = getattr(endpoint, backup_field)
        setattr(endpoint, backup_field, kwargs.get(backup_field) or origin[backup_field])

    origin_endpoint = self.endpoint
    self.endpoint = endpoint

    meta = self.metadata_class()
    data = meta.determine_metadata(request, self)

    for backup_field in backup_fields:
        setattr(endpoint, backup_field, origin[backup_field])

    self.endpoint = origin_endpoint

    return Response(data)


def list_route(methods=None, serializer=None, fieldsets=None, endpoint=None, list_display=None,
               list_editable=None, **kwargs):
    methods = ['get'] if (methods is None) else methods
    if 'options' not in methods:
        methods.extend(['options'])

    def decorator(func):
        def metadata_wrapper(self, request, *args, **kwargs):
            if request.method == 'OPTIONS':
                return metadata(
                    self, request, serializer=serializer, fieldsets=fieldsets, endpoint=endpoint,
                    list_display=list_display, list_editable=list_editable, * args, **kwargs
                )

            return func(self, request, *args, **kwargs)

        metadata_wrapper.bind_to_methods = methods
        metadata_wrapper.detail = False
        metadata_wrapper.kwargs = kwargs
        return metadata_wrapper
    return decorator


def detail_route(methods=None, serializer=None, fieldsets=None, endpoint=None, list_display=None, ** kwargs):
    methods = ['get'] if (methods is None) else methods
    if 'options' not in methods:
        methods.extend(['options'])

    def decorator(func):
        def metadata_wrapper(self, request, *args, **kwargs):
            if request.method == 'OPTIONS':
                return metadata(
                    self, request, serializer=serializer, fieldsets=fieldsets, endpoint=endpoint,
                    list_display=list_display, *args, **kwargs
                )

            return func(self, request, *args, **kwargs)

        metadata_wrapper.bind_to_methods = methods
        metadata_wrapper.detail = True
        metadata_wrapper.kwargs = kwargs
        return metadata_wrapper
    return decorator
