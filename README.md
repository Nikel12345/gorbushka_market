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
    core/            общие вещи: базовые модели, health-check
    users/           кастомная модель пользователя
  requirements/      base / dev / prod

frontend/src/
  app/               корень приложения: провайдеры, глобальные стили
  pages/             страницы
  shared/
    api/             HTTP-клиент и запросы к backend
    config/          конфиг из env
```

## Соглашения

- **Новое доменное приложение** — `backend/apps/<name>/`, регистрируется в `LOCAL_APPS` и подключается в `config/api_v1.py`.
- **Бизнес-логика — в сервисном слое** (`apps/<name>/services.py`), а не во view/serializer.
  Там же задаются границы транзакций (`transaction.atomic`, `select_for_update`) —
  это позволит делать атомарные операции (заказы, остатки, платежи) без переписывания view.
- **БД** задаётся через `DATABASE_URL` — переход с SQLite на PostgreSQL без изменений кода.
- **API версионируется** префиксом `/api/v1/`.
