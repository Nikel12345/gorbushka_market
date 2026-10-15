"""
Keyset (курсорная) пагинация для бесконечных лент.

Как работает:
1. К queryset уже применены фильтры и поиск (это делает view до пагинации).
2. Он сортируется по (поле сортировки, id) — id делает порядок однозначным
   даже при одинаковых значениях (например, много товаров по одной цене).
3. Сервер отдаёт порцию и `next_cursor` — закодированную позицию последнего
   элемента: (сортировка, значение поля, id).
4. Следующий запрос с тем же набором фильтров и `?cursor=...` превращается в
   WHERE <фильтры> AND (field, id) > (value, last_id)  LIMIT page_size.

В отличие от ?page=N (OFFSET): нет дублей и пропусков, если во время прокрутки
появились/исчезли элементы, и скорость не падает на глубоких страницах.
При смене фильтров или сортировки клиент начинает ленту заново, без курсора.

Ограничение: поле сортировки не должно быть nullable.
"""
import base64
import binascii
import json
from dataclasses import dataclass

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import BasePagination
from rest_framework.response import Response


@dataclass(frozen=True)
class SortOption:
    field: str
    descending: bool = False


class KeysetPagination(BasePagination):
    page_size = 20
    max_page_size = 50
    page_size_query_param = "page_size"
    cursor_query_param = "cursor"
    sort_query_param = "sort"

    # Переопределяются в наследниках: {"имя_в_api": SortOption(...)}
    sort_options: dict[str, SortOption] = {"id": SortOption("id")}
    default_sort = "id"

    invalid_cursor_message = "Некорректный курсор. Начните ленту заново."

    def paginate_queryset(self, queryset, request, view=None):
        sort_name = self._get_sort_name(request)
        sort = self.sort_options[sort_name]
        page_size = self._get_page_size(request)

        direction = "-" if sort.descending else ""
        queryset = queryset.order_by(f"{direction}{sort.field}", f"{direction}pk")

        cursor = self._decode_cursor(request, sort_name, sort, queryset.model)
        if cursor is not None:
            value, pk = cursor
            op = "lt" if sort.descending else "gt"
            queryset = queryset.filter(
                Q(**{f"{sort.field}__{op}": value}) | Q(**{sort.field: value, f"pk__{op}": pk})
            )

        # Берём на один больше, чтобы понять, есть ли следующая порция, без COUNT(*)
        items = list(queryset[: page_size + 1])
        has_next = len(items) > page_size
        items = items[:page_size]

        self.next_cursor = (
            self._encode_cursor(sort_name, getattr(items[-1], sort.field), items[-1].pk)
            if has_next
            else None
        )
        return items

    def get_paginated_response(self, data):
        return Response({"next_cursor": self.next_cursor, "results": data})

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "required": ["next_cursor", "results"],
            "properties": {
                "next_cursor": {"type": "string", "nullable": True},
                "results": schema,
            },
        }

    # --- helpers ---

    def _get_sort_name(self, request) -> str:
        sort_name = request.query_params.get(self.sort_query_param) or self.default_sort
        if sort_name not in self.sort_options:
            raise ValidationError(
                {self.sort_query_param: [f"Допустимые значения: {', '.join(self.sort_options)}."]}
            )
        return sort_name

    def _get_page_size(self, request) -> int:
        raw = request.query_params.get(self.page_size_query_param)
        if raw is None:
            return self.page_size
        try:
            size = int(raw)
        except ValueError:
            size = 0
        if not 1 <= size <= self.max_page_size:
            raise ValidationError(
                {self.page_size_query_param: [f"Число от 1 до {self.max_page_size}."]}
            )
        return size

    def _encode_cursor(self, sort_name: str, value, pk) -> str:
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        payload = json.dumps({"s": sort_name, "v": str(value), "k": pk}, separators=(",", ":"))
        return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

    def _decode_cursor(self, request, sort_name: str, sort: SortOption, model):
        raw = request.query_params.get(self.cursor_query_param)
        if not raw:
            return None

        try:
            padded = raw + "=" * (-len(raw) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
            # Курсор от другой сортировки бессмыслен — значения другого поля
            if payload["s"] != sort_name:
                raise ValueError("sort mismatch")
            value = model._meta.get_field(sort.field).to_python(payload["v"])
            pk = model._meta.pk.to_python(payload["k"])
            if value is None or pk is None:
                raise ValueError("empty position")
        except (ValueError, TypeError, KeyError, binascii.Error, DjangoValidationError, UnicodeDecodeError):
            raise ValidationError({self.cursor_query_param: [self.invalid_cursor_message]})

        return value, pk
