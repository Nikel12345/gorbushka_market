"""
Корневой роутинг API v1.
Каждое приложение подключает здесь свои urls; новая несовместимая версия
API заводится отдельным модулем (api_v2.py) без поломки текущих клиентов.
"""
from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.urls")),
    path("auth/", include("apps.users.urls")),
    path("catalog/", include("apps.catalog.urls")),
    path("shops/", include("apps.shops.urls")),
    # Страница текущего пользователя (покупателя). Как и seller/ — маршруты
    # собираются из доменных приложений.
    path(
        "me/",
        include(
            [
                path("", include("apps.users.me_urls")),
                path("", include("apps.wallet.me_urls")),
                path("", include("apps.orders.me_urls")),
            ]
        ),
    ),
    # Кабинет продавца. Каждое доменное приложение отдаёт свои seller-маршруты.
    path(
        "seller/",
        include(
            [
                path("", include("apps.shops.seller_urls")),
                path("", include("apps.catalog.seller_urls")),
                path("", include("apps.orders.seller_urls")),
            ]
        ),
    ),
]
