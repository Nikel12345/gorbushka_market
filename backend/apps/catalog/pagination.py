from apps.core.pagination import KeysetPagination, SortOption


class ProductFeedPagination(KeysetPagination):
    page_size = 20
    max_page_size = 50
    sort_options = {
        "new": SortOption("created_at", descending=True),
        "price_asc": SortOption("price"),
        "price_desc": SortOption("price", descending=True),
    }
    default_sort = "new"
