# Gorbushka Market

Маркетплейс для рынка. Монорепозиторий: `backend/` (Django + DRF) и `frontend/` (React + TypeScript + Vite).

## Быстрый старт

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements/dev.txt
copy .env.example .env          # по желанию: без .env работают dev-дефолты
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver      # http://127.0.0.1:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

В dev-режиме Vite проксирует `/api/*` на Django, поэтому фронт и API работают с одного origin.

## Структура

```
backend/
  config/
    settings/        base.py — общее, dev.py / prod.py — по окружениям
    urls.py          корневой роутинг (admin, api/v1/)
    api_v1.py        роуты API v1: сюда подключаются urls приложений
  apps/
    core/            общее: базовые модели, BaseFilterSet, KeysetPagination, BusinessError
    users/           пользователь (вход по email) и авторизация
    shops/           магазины; проверка доступа — Shop.objects.managed_by(user)
    catalog/         товары (привязаны к магазину), публичная лента, поиск (catalog/search.py)
    orders/          заказы и позиции; оформление — orders.services.create_order
    wallet/          баланс пользователя и журнал операций; изменение — wallet.services.change_balance
  requirements/      base / dev / prod

frontend/src/
  app/               корень приложения: провайдеры, роутер, layout, стили
  pages/             страницы (home, login, register, profile)
  features/
    auth/            контекст авторизации, useAuth, guards (RequireAuth / GuestOnly)
  shared/
    api/             HTTP-клиент (cookie + CSRF) и запросы к backend
    ui/              переиспользуемые UI-компоненты
    config/          конфиг из env
```

## Авторизация

Сессии Django (HttpOnly cookie `sessionid`) + CSRF. Один тип аккаунта для покупателя и продавца, вход по email.

| Метод | URL | Описание |
|---|---|---|
| GET  | `/api/v1/auth/csrf/`     | выставляет cookie `csrftoken` |
| POST | `/api/v1/auth/register/` | `{email, password, first_name?, last_name?}` → пользователь, сразу залогинен |
| POST | `/api/v1/auth/login/`    | `{email, password}` → пользователь |
| POST | `/api/v1/auth/logout/`   | 204 |
| GET  | `/api/v1/auth/me/`       | текущий пользователь, 403 если не авторизован |

- Все небезопасные запросы (POST/PUT/PATCH/DELETE) требуют заголовок `X-CSRFToken` со значением cookie `csrftoken` — `shared/api/client.ts` делает это сам.
- login/register ограничены по частоте (`THROTTLE_RATE_AUTH`, по умолчанию 10/min с IP).
- Email хранится в нижнем регистре, вход регистронезависимый.

## Лента товаров (главная)

Публичные эндпоинты, авторизация не нужна.

| Метод | URL | Описание |
|---|---|---|
| GET | `/api/v1/catalog/products/` | лента товаров на продаже |
| GET | `/api/v1/catalog/products/{id}/` | товар (с описанием и остатком) |

Параметры ленты (все необязательные, комбинируются):

| Параметр | Пример | |
|---|---|---|
| `q` | `чехол iphone` | поиск: все слова в названии/описании, без учёта регистра, ё = е |
| `shop` | `12` | товары магазина |
| `price_min`, `price_max` | `1000`, `5000` | диапазон цены, включительно |
| `in_stock` | `true` | только в наличии |
| `sort` | `new` (по умолчанию), `price_asc`, `price_desc` | сортировка |
| `page_size` | `20` (по умолчанию), до 50 | размер порции |
| `cursor` | значение `next_cursor` | следующая порция |

Ответ: `{"next_cursor": "..." | null, "results": [...]}`.

**Бесконечная прокрутка (курсорная пагинация).** Первый запрос — без `cursor`. Следующий — с теми же
фильтрами и `cursor=<next_cursor>`. `next_cursor: null` — лента закончилась. При изменении любого
фильтра или сортировки ленту начинают заново без курсора (курсор от другой сортировки вернёт 400).
Курсор — непрозрачная строка, фронт не должен её разбирать. Внутри — позиция последнего товара
`(значение поля сортировки, id)`, а запрос строится как `WHERE <фильтры> AND (field, id) > (позиция)`,
поэтому нет дублей/пропусков при добавлении товаров во время прокрутки и нет замедления на глубине.
Общего количества (`count`) нет намеренно — это лишний `COUNT(*)` на каждый запрос.

## Магазин (публичная страница)

| Метод | URL | Описание |
|---|---|---|
| GET | `/api/v1/shops/{shop_id}/` | магазин для покупателя: `id, name, description, products_count, created_at` |

Товары магазина — та же лента: `GET /api/v1/catalog/products/?shop={shop_id}` (все фильтры и курсор работают).

## Страница пользователя

Все эндпоинты требуют авторизации и работают с текущим пользователем.

| Метод | URL | Описание |
|---|---|---|
| GET   | `/api/v1/me/profile/` | профиль |
| PATCH | `/api/v1/me/profile/` | `{first_name?, last_name?}` → профиль (email не меняется) |
| GET   | `/api/v1/me/balance/` | `{"balance": "1500.50"}` |
| GET   | `/api/v1/me/orders/` | история заказов, курсор (как в ленте) |

Параметры истории заказов (`OrderFilter` — тот же, что у продавца):

| Параметр | Пример | |
|---|---|---|
| `status` | `new`, можно несколько: `?status=new&status=confirmed` | `new`, `confirmed`, `completed`, `cancelled` |
| `shop` | `12` | заказы в магазине |
| `date_from`, `date_to` | `2026-02-01` | дата оформления, включительно (время Москвы) |
| `sort` | `new` (по умолчанию), `old`, `total_desc`, `total_asc` | |
| `page_size`, `cursor` | | как в ленте товаров |

## Кабинет продавца

Все эндпоинты требуют авторизации. Чужой или несуществующий магазин/товар — `404`.

| Метод | URL | Описание |
|---|---|---|
| GET    | `/api/v1/seller/profile/` | пользователь + `shops: [{id, name}]` |
| GET    | `/api/v1/seller/shops/` | мои магазины |
| POST   | `/api/v1/seller/shops/` | `{name, description?}` — создать магазин |
| GET    | `/api/v1/seller/shops/{shop_id}/` | магазин: публичные поля + служебные |
| PATCH  | `/api/v1/seller/shops/{shop_id}/` | `{name?, description?}` |
| GET    | `/api/v1/seller/shops/{shop_id}/products/` | товары на продаже (пагинация, фильтры ленты: `q`, `price_min`, ...) |
| POST   | `/api/v1/seller/shops/{shop_id}/products/` | `{title, price, quantity?, description?, image?}` — добавить товар |
| GET    | `/api/v1/seller/shops/{shop_id}/products/{id}/` | товар |
| PATCH  | `/api/v1/seller/shops/{shop_id}/products/{id}/` | `{title?, description?, price?, quantity?, image?}` — JSON или multipart |
| DELETE | `/api/v1/seller/shops/{shop_id}/products/{id}/` | снять с продажи (мягкое удаление) |
| GET    | `/api/v1/seller/shops/{shop_id}/orders/` | история заказов, новые сверху; фильтры `OrderFilter` (как у покупателя) |

- Списки товаров и заказов пагинированы: `{count, next, previous, results}`, `?page=N`, по 20.
- Денежные поля приходят строками (`"79990.00"`) — без потери точности.
- Товар не удаляется физически (на него ссылаются заказы), а получает статус `archived`.
- Изменять/удалять товар может только тот, кто управляет магазином (`Shop.objects.managed_by`); иначе `404`.
  `shop` и `status` через PATCH не меняются.

### Фото товара

- Поле `image` есть в кабинете, ленте и на странице товара: строка-URL (`/media/products/<uuid>.png`) или `null`.
  **Фронт должен показывать заглушку при `null`.**
- Загрузка — `multipart/form-data` (`POST` при создании или `PATCH`), поле `image`. Убрать фото —
  `PATCH {"image": null}` (JSON) или пустое `image=` в multipart. Без поля `image` фото не меняется.
- Проверки: файл должен быть картинкой (Pillow), размер — до `PRODUCT_IMAGE_MAX_MB` (5 МБ).
  Имя файла заменяется на случайное. Старый файл удаляется после успешного сохранения.
- Если файл пропал из хранилища — API не падает. В dev Vite проксирует `/media` на Django;
  в prod `/media/` раздаёт nginx (или подключается S3-хранилище — URL станут абсолютными).
- Позиции заказа хранят снимок названия и цены на момент покупки.

## Тесты

```bash
cd backend && python manage.py test     # автоматически использует config.settings.test
cd frontend && npm run lint && npm run build
```

## Соглашения

- **Одна логика на сущность — для всех сторон.** Один `FilterSet` на сущность (`ProductFilter`, `OrderFilter`),
  одна пагинация на тип списка (наследники `core.pagination.KeysetPagination`), один базовый сериализатор,
  от которого наследуются варианты для продавца/покупателя/публики (`OrderSerializer` → `SellerOrderSerializer`,
  `BuyerOrderSerializer`; `ShopPublicSerializer` → `SellerShopSerializer`). Кто что видит — задаёт queryset view,
  а не отдельный фильтр. Никаких `UserGoodsFilter`/`SellerProductFilter`.
- **Маршруты по аудиториям** собираются в `config/api_v1.py` из доменных приложений: `seller_urls.py` → `/seller/`,
  `me_urls.py` → `/me/`, `urls.py` → публичные.
- **Новое доменное приложение** — `backend/apps/<name>/`, регистрируется в `LOCAL_APPS` и подключается в `config/api_v1.py`.
- **Бизнес-логика — в сервисном слое** (`apps/<name>/services.py`), а не во view/serializer.
  Там же задаются границы транзакций (`transaction.atomic`, `select_for_update`) —
  это позволит делать атомарные операции (заказы, остатки, платежи) без переписывания view.
- **БД** задаётся через `DATABASE_URL` — переход с SQLite на PostgreSQL без изменений кода.
- **API версионируется** префиксом `/api/v1/`.
