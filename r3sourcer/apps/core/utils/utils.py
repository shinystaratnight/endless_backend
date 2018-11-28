from urllib.parse import urlparse

from easy_thumbnails.alias import aliases


def get_thumbnail_picture(picture, alias):
    if picture:
        try:
            return picture.get_thumbnail(aliases.get(alias)).url
        except Exception:
            pass


def get_host(request):
    host_parts = urlparse(request.META.get('HTTP_ORIGIN', request.get_host()))
    return host_parts.netloc or host_parts.path
