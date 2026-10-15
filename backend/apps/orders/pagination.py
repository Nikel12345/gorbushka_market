from apps.core.pagination import KeysetPagination, SortOption


class OrderHistoryPagination(KeysetPagination):
    """Курсорная история заказов (бесконечная прокрутка)."""

    page_size = 20
    max_page_size = 50
    sort_options = {
        "new": SortOption("created_at", descending=True),
        "old": SortOption("created_at"),
        "total_desc": SortOption("total_amount", descending=True),
        "total_asc": SortOption("total_amount"),
    }
    default_sort = "new"
