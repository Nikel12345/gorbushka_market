from rest_framework import serializers


class ImageUrlField(serializers.ImageField):
    """
    Картинка в API для всех сущностей (товар, позже — магазин, аватар...).

    Запись: обычная загрузка файла (multipart/form-data); null или пустое
    значение — убрать картинку.
    Чтение: URL от хранилища или null. Абсолютный URL не строим: локально это
    /media/... (тот же origin, что у фронта), у S3/CDN хранилище само отдаёт
    абсолютный. Если картинки нет или с файлом что-то не так — null, а не 500.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("allow_null", True)
        super().__init__(**kwargs)

    def to_representation(self, value):
        if not value:
            return None
        try:
            return value.url
        except (ValueError, OSError):
            return None
