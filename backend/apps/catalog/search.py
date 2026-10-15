"""
Поиск по товарам. Вся логика поиска — здесь: при переходе на полнотекстовый
поиск PostgreSQL / trigram / внешний движок (Meilisearch, Elasticsearch)
меняется только этот модуль.

Сейчас: нормализованное поле Product.search_text (нижний регистр, ё → е)
и вхождение каждого слова запроса. Нормализация в Python, а не в БД, потому что
LOWER/LIKE в SQLite не работают с кириллицей.
"""
MAX_QUERY_TERMS = 10


def normalize(text: str) -> str:
    return " ".join(text.lower().replace("ё", "е").split())


def build_search_text(*parts: str) -> str:
    return normalize(" ".join(part for part in parts if part))


def search_products(queryset, query: str):
    """Все слова запроса должны встречаться в названии или описании."""
    for term in normalize(query).split()[:MAX_QUERY_TERMS]:
        queryset = queryset.filter(search_text__contains=term)
    return queryset
