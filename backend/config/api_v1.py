"""
Корневой роутинг API v1.
Каждое приложение подключает здесь свои urls; новая несовместимая версия
API заводится отдельным модулем (api_v2.py) без поломки текущих клиентов.
"""
from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.urls")),
    path("auth/", include("apps.users.urls")),
    path(
        "catalog/",
        include(
            [
                path("", include("apps.catalog.urls")),
                path("", include("apps.reviews.urls")),
                path("", include("apps.recommendations.urls")),
            ]
        ),
    ),
    path("shops/", include("apps.shops.urls")),
    path("delivery/", include("apps.delivery.urls")),
    path("promo/", include("apps.promo.urls")),
    path("currency/", include("apps.currency.urls")),
    # Страница текущего пользователя (покупателя). Как и admin/ — маршруты
    # собираются из доменных приложений.
    path(
        "me/",
        include(
            [
                path("", include("apps.users.me_urls")),
                path("", include("apps.wallet.me_urls")),
                path("", include("apps.orders.me_urls")),
                path("", include("apps.cart.me_urls")),
                path("", include("apps.reviews.me_urls")),
            ]
        ),
    ),
    # Сотрудники маркета (сейчас — is_staff): доставка курьером маркета.
    path("market/", include("apps.orders.market_urls")),
    # Админка магазина (сотрудники, is_staff). Каждое доменное приложение отдаёт свои admin-маршруты.
    path(
        "admin/",
        include(
            [
                path("", include("apps.shops.admin_urls")),
                path("", include("apps.catalog.admin_urls")),
                path("", include("apps.orders.admin_urls")),
                path("", include("apps.reviews.admin_urls")),
            ]
        ),
    ),
]
