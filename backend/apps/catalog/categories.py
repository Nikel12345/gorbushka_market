"""
Дерево категорий. Категорий немного (сотни), поэтому дерево читается целиком одним
запросом и обходится в Python: подкатегории для фильтра ленты, путь для «хлебных крошек»,
порядок и глубина для списка, число товаров вместе с подкатегориями.
"""
from collections import defaultdict
from collections.abc import Iterator

from django.db.models import Count

from apps.core.exceptions import BusinessError

from .models import Category, Product


class CategoryTree:
    def __init__(self, categories):
        self.by_id: dict[int, Category] = {category.id: category for category in categories}
        self.children: dict[int | None, list[Category]] = defaultdict(list)
        for category in self.by_id.values():
            self.children[category.parent_id].append(category)
        for siblings in self.children.values():
            siblings.sort(key=lambda category: (category.sort_order, category.name, category.id))

    @classmethod
    def load(cls) -> "CategoryTree":
        return cls(Category.objects.all())

    def walk(self, parent_id: int | None = None, depth: int = 0) -> Iterator[tuple[Category, int]]:
        """Все категории сверху вниз: родитель, затем его подкатегории по порядку. С глубиной (корень — 0)."""
        for category in self.children.get(parent_id, []):
            yield category, depth
            yield from self.walk(category.id, depth + 1)

    def subtree_ids(self, pk: int) -> set[int]:
        """Категория и все её подкатегории. Нет такой категории — пусто."""
        if pk not in self.by_id:
            return set()
        return {pk, *(category.id for category, _ in self.walk(pk))}

    def path(self, pk: int) -> list[Category]:
        """От корня до категории."""
        path, seen = [], set()
        category = self.by_id.get(pk)
        while category is not None and category.id not in seen:
            seen.add(category.id)
            path.append(category)
            category = self.by_id.get(category.parent_id)
        return path[::-1]

    def allows(self, characteristic, category_id: int | None) -> bool:
        """Характеристика доступна товару категории category_id: общая или привязана к ней или выше."""
        if characteristic.category_id is None:
            return True
        return category_id is not None and any(c.id == characteristic.category_id for c in self.path(category_id))

    def branch_ids(self, pk: int) -> set[int]:
        """Категории, товары которых видят характеристики категории pk, и наоборот: путь до корня и поддерево."""
        return {category.id for category in self.path(pk)} | self.subtree_ids(pk)

    def products_count(self) -> dict[int, int]:
        """Товары на продаже в категории вместе с подкатегориями: {category_id: n}."""
        own = dict(
            Product.objects.on_sale()
            .filter(category__isnull=False)
            .values_list("category_id")
            .annotate(n=Count("id"))
            .order_by()
        )
        total: dict[int, int] = {}

        def count(category: Category) -> int:
            total[category.id] = own.get(category.id, 0) + sum(count(child) for child in self.children[category.id])
            return total[category.id]

        for root in self.children[None]:
            count(root)
        return total


def check_parent(category: Category, parent: Category | None) -> None:
    """Перенос под parent: нельзя внутрь самой категории или её подкатегорий — дерево замкнётся."""
    if parent is None or category.pk is None:
        return
    if parent.pk in CategoryTree.load().subtree_ids(category.pk):
        raise BusinessError("Нельзя перенести категорию внутрь неё самой.", code="category_cycle")
