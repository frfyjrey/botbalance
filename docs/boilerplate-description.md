# 📄 1. boilerplate-description.md

## 🎯 Цель

Собрать минималистичный, но полный **boilerplate-проект** для будущих приложений:

* Backend → Django + DRF + Celery (сразу с Redis и Postgres).
* Frontend → Vite + React + TypeScript.
* Интеграция через API с JWT аутентификацией.
* CI/CD → базовый GitHub Actions (линтеры + тесты).
* Dev experience → OrbStack (docker-compose для Postgres + Redis), Makefile, единый venv (через **uv**).

В этом boilerplate **нет бизнес-логики** (бота, ордеров и т.п.), только структура и “hello world” endpoints.
Он должен быть универсальным для любого будущего проекта (например, botbalance).

---

## 📂 Структура репозитория

```
boilerplate/
  backend/
    app/
      settings/
        base.py
        local.py
        prod.py
      api/             # DRF views (health, auth)
      core/            # утилиты, сервисы
      tasks/           # Celery tasks (echo, heartbeat)
      urls.py
      wsgi.py
      asgi.py
    manage.py
    pyproject.toml / requirements.txt
  frontend/
    src/
      pages/           # Login, Dashboard
      lib/             # api.ts (fetch wrapper)
    package.json
    vite.config.ts
  ops/
    agent/             # журнал ИИ-агента
  docker-compose.yml   # Postgres + Redis для локалки
  Makefile             # dev/lint/test/migrate
  .github/workflows/ci.yml
  README.md
```

---

## 🔙 Backend (Django + DRF + Celery)

* **Фреймворки**: Django, DRF, Celery, Redis, PostgreSQL.
* **Аутентификация**: JWT (djangorestframework-simplejwt).
* **Endpoints**:

  * `POST /api/auth/login` — выдача токена.
  * `GET /api/health` — проверка DB/Redis.
  * `GET /api/version` — версия API.
  * `POST /api/tasks/echo` → создаёт Celery-задачу, возвращает task\_id.
  * `GET /api/tasks/status?task_id=...` → статус задачи.
* **Celery**:

  * broker = Redis
  * task example: echo (вернёт текст), heartbeat (пишет лог).
* **Config**:

  * `base.py` — общие настройки.
  * `local.py` — DEBUG, sqlite/postgres локально.
  * `prod.py` — настройки для GCP (Cloud SQL + Upstash).
* **ENV**:

  ```
  DJANGO_SECRET_KEY=dev-secret
  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/boilerplate
  REDIS_URL=redis://localhost:6379/0
  ALLOWED_HOSTS=localhost,127.0.0.1
  CORS_ALLOWED_ORIGINS=http://localhost:5173
  ```

---

## 🔙 Frontend (Vite + React + TS)

* **Фреймворки**: React, Vite, TypeScript.
* **Страницы**:

  * `Login` — форма логина, запрос к `/auth/login`.
  * `Dashboard` — “Hello, user!”, запрос к `/health`.
* **API клиент** (`lib/api.ts`):

  * хранение токена в localStorage,
  * axios/fetch wrapper,
  * перехватчик ошибок (401 → logout).
* **ENV**:

  ```
  VITE_API_BASE=http://localhost:8000
  ```

---

## 🛠 Dev Experience

* **OrbStack/docker-compose**: поднимаем Postgres и Redis.
* **uv**: единое окружение для Python.
* **Makefile**:

  * `make dev` → backend (uv run), worker (celery), frontend (vite).
  * `make lint` → ruff, black, isort, mypy (backend), eslint, tsc (frontend).
  * `make test` → pytest, vitest.
  * `make migrate` → миграции.
* **CI (GitHub Actions)**:

  * Линтеры: ruff, mypy, eslint, tsc.
  * Тесты: pytest (бэк), vitest (фронт).
  * Сервис Postgres для тестов.

---

## 🚦 Definition of Done

* Локально: `make dev` поднимает всё → можно открыть фронт, залогиниться, увидеть Dashboard и health-check.
* CI зелёный: линтеры + тесты проходят.
* Celery таски работают: `POST /api/tasks/echo` возвращает результат через status API.
* Всё описано в `README.md`.
