from django.utils import six
from django.utils.functional import lazy

try:  # pragma: no cover
    from django.utils.text import format_lazy  # Django 1.11+
except ImportError:  # pragma: no cover
    def format_wrapper(format_text, *args, **kwargs):
        return format_text.format(*args, **kwargs)

    format_lazy = lazy(format_wrapper, six.text_type)
