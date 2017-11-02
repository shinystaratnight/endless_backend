import operator
from functools import reduce

from django.db.models import Q
from django.utils.crypto import get_random_string


class GenerateAuthTokenMixin(object):

    @classmethod
    def generate_auth_token(cls, token_field_name='auth_token', token_field_names=None, length=8):
        while True:
            token = get_random_string(length=length)
            if token_field_names is None:
                lookup = Q(**{token_field_name: token})
            else:
                lookups = [Q(**{field_name: token}) for field_name in token_field_names]
                lookup = reduce(operator.__or__, lookups)
            try:
                cls.objects.get(lookup)
            except cls.DoesNotExist:
                return token
