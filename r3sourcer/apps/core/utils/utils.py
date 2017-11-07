from easy_thumbnails.alias import aliases


def get_thumbnail_picture(picture, alias):
    if picture:
        try:
            return picture.get_thumbnail(aliases.get(alias)).url
        except Exception:
            pass
