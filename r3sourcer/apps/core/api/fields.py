import copy
from datetime import timedelta

from django.utils import six, timezone
from imghdr import what
from rest_framework import serializers

from ..utils.utils import get_thumbnail_picture


class ApiAbsoluteUrlMixin():
    def get_absolute(self, value):
        if not value:
            return value
        request = self.context.get('request', None)
        if request is not None:
            return request.build_absolute_uri(value)
        return value


class ApiBaseRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        str_val = str(value)
        data = {
            'id': value.id,
            'name': str_val,
            '__str__': str_val,
        }

        return data


class ApiDateTimeTzField(serializers.DateTimeField):

    def to_representation(self, value):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return super().to_representation(value)


class ApiBase64ImageField(serializers.ImageField):
    """
    A Django REST framework field for handling image-uploads through raw post data.
    It uses base64 for encoding and decoding the contents of the file.
    """

    def to_internal_value(self, data):
        from django.core.files.base import ContentFile
        import base64
        import six
        import uuid

        # Check if this is a base64 string
        if isinstance(data, six.string_types):
            if 'data:' in data and ';base64,' in data:
                header, data = data.split(';base64,')

            try:
                decoded_file = base64.b64decode(data.encode('ascii'))
            except (TypeError, UnicodeEncodeError):
                self.fail('invalid_image')

            file_name = str(uuid.uuid4())
            file_extension = self.get_file_extension(file_name, decoded_file)

            complete_file_name = "%s.%s" % (file_name, file_extension, )

            data = ContentFile(decoded_file, name=complete_file_name)

        return super().to_internal_value(data)

    def get_file_extension(self, file_name, decoded_file):
        extension = what(file_name, decoded_file)
        extension = "jpg" if extension == "jpeg" else extension

        return extension


class ApiContactPictureField(ApiAbsoluteUrlMixin, ApiBase64ImageField):

    def to_representation(self, value):
        data = {
            'thumb': self.get_absolute(get_thumbnail_picture(value, 'micro')),
            'origin': self.get_absolute(get_thumbnail_picture(value, 'large')),
        }

        return data


class ApiChoicesField(serializers.ChoiceField):

    def __init__(self, choices, **kwargs):
        super().__init__(choices, **kwargs)

        self.choice_strings_to_values = {
            self._convert_to_text(key): key for key in self.choices.keys()
        }

    def _convert_to_text(self, val):
        if isinstance(val, timedelta):
            val = int(val.total_seconds())

        return six.text_type(val)

    def to_internal_value(self, data):
        if data == '' and self.allow_blank:
            return ''

        try:
            data = int(float(data))
        except ValueError:
            pass

        try:
            return self.choice_strings_to_values[six.text_type(data)]
        except (KeyError, ValueError):
            self.fail('invalid_choice', input=data)


class EmptyNullField(serializers.Field):

    def run_validation(self, data=serializers.empty):
        if data is None:
            data = serializers.empty

        return super().run_validation(data)

    @classmethod
    def from_field(cls, field):
        field_class = field.__class__

        except_classes = (serializers.BooleanField,
                          serializers.NullBooleanField)
        if issubclass(field_class, except_classes):
            return serializers.NullBooleanField(*field._args, **field._kwargs)

        class Internal(cls, field_class):
            pass

        kwargs = copy.copy(field._kwargs)
        kwargs['allow_null'] = True

        return Internal(*field._args, **kwargs)
