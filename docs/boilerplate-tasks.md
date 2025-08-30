# 📄 2. boilerplate-tasks.md

## Этап 0. Подготовка

1. Создать репозиторий `boilerplate/`.
2. Добавить `.gitignore`, `.dockerignore`.
3. Создать `README.md` (цель проекта + инструкции).

---

## Этап 1. Backend

1. Инициализировать Django проект `app/`.
2. Добавить DRF (djangorestframework).
3. Настроить `settings/base.py`, `local.py`, `prod.py`.
4. Подключить Postgres (через docker-compose).
5. Подключить Redis (через docker-compose).
6. Добавить Celery конфигурацию (`tasks/`, echo/heartbeat).
7. Реализовать JWT аутентификацию.
8. Реализовать эндпоинты:

   * `/api/auth/login`
   * `/api/health`
   * `/api/version`
   * `/api/tasks/echo`, `/api/tasks/status`
9. Тесты: `pytest` для health и echo.

---

## Этап 2. Frontend

1. Инициализировать Vite + React + TS.
2. Добавить ESLint, Prettier, TS config.
3. Реализовать API-клиент (`lib/api.ts`).
4. Реализовать страницы:

   * `Login` (форма логина).
   * `Dashboard` (Hello + health).
5. Тесты: `vitest` для smoke-теста.

---

## Этап 3. Dev Experience

1. Добавить `docker-compose.yml` (Postgres, Redis).
2. Настроить Makefile:

   * `dev`, `lint`, `test`, `migrate`.
3. Настроить CI (GitHub Actions):

   * сервис Postgres,
   * шаги: lint + pytest, lint + vitest.
4. Проверить end-to-end: login → dashboard → health → echo-task.

---

## Этап 4. Завершение

1. Проверить `make dev` на чистой машине.
2. Проверить `make lint && make test`.
3. Проверить CI.
4. Финализировать `README.md`.
