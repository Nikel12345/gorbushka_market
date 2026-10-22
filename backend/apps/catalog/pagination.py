from apps.core.pagination import KeysetPagination, SortOption


class ProductFeedPagination(KeysetPagination):
    page_size = 20
    max_page_size = 50
    sort_options = {
        "new": SortOption("created_at", descending=True),
        # Цена в рублях растёт вместе с ценой в долларах
        "price_asc": SortOption("price_usd"),
        "price_desc": SortOption("price_usd", descending=True),
    }
    default_sort = "new"
