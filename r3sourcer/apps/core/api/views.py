from rest_framework.views import exception_handler


def core_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        new_response = {
            'status': 'error',
            'errors': response.data
        }
        response.data = new_response

    return response
