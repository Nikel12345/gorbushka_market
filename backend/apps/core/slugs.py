from django.utils.text import slugify

_RU = {
    **dict(zip("абвгдеёзиклмнопрстуфыэ", "abvgdeeziklmnoprstufye")),
    "ж": "zh", "й": "y", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ю": "yu", "я": "ya",
    "ъ": "", "ь": "",
}


def slugify_ru(text: str) -> str:
    """Адрес из русского текста: «Смартфоны и гаджеты» → smartfony-i-gadzhety."""
    return slugify("".join(_RU.get(char, char) for char in text.lower()))
