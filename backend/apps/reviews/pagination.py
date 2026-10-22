from apps.core.pagination import KeysetPagination, SortOption


class ReviewPagination(KeysetPagination):
    """Отзывы порциями («Показать ещё»): новые сверху или по оценке."""

    page_size = 20
    max_page_size = 50
    sort_options = {
        "new": SortOption("created_at", descending=True),
        "rating_desc": SortOption("rating", descending=True),
        "rating_asc": SortOption("rating"),
    }
    default_sort = "new"
