from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class MaxFileSizeValidator:
    """
    Ограничение размера загружаемого файла.
    Лимит — число байт или имя настройки (читается в момент проверки,
    поэтому его можно менять через env/override_settings без перезапуска импорта).
    """

    def __init__(self, max_bytes: int | None = None, *, setting: str | None = None):
        if (max_bytes is None) == (setting is None):
            raise ValueError("Укажите либо max_bytes, либо setting.")
        self.max_bytes = max_bytes
        self.setting = setting

    def get_limit(self) -> int:
        return self.max_bytes if self.max_bytes is not None else getattr(settings, self.setting)

    def __call__(self, file):
        limit = self.get_limit()
        if file and file.size > limit:
            raise ValidationError(
                f"Файл слишком большой: максимум {limit / (1024 * 1024):g} МБ.",
                code="file_too_large",
            )

    def __eq__(self, other):
        return (
            isinstance(other, MaxFileSizeValidator)
            and self.max_bytes == other.max_bytes
            and self.setting == other.setting
        )
