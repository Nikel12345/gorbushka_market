"""
Корневой роутинг API v1.
Каждое приложение подключает здесь свои urls; новая несовместимая версия
API заводится отдельным модулем (api_v2.py) без поломки текущих клиентов.
"""
from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.urls")),
]
