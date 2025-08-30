# 📋 Boilerplate Tasks

Пошаговый план создания Django + React boilerplate проекта

---

## 🚀 Этап 0. Подготовка

### ✅ Задачи:

1. **📁 Создать репозиторий** `boilerplate/`
2. **🚫 Добавить игнор-файлы** `.gitignore`, `.dockerignore` 
3. **📖 Создать документацию** `README.md` (цель проекта + инструкции)

---

## 🔧 Этап 1. Backend

### ✅ Задачи:

1. **🏗️ Инициализировать Django** проект `app/`
2. **📦 Добавить DRF** (`djangorestframework`)
3. **⚙️ Настроить конфигурацию** `settings/base.py`, `local.py`, `prod.py`
4. **🐘 Подключить PostgreSQL** (через docker-compose)
5. **🔥 Подключить Redis** (через docker-compose)
6. **📋 Добавить Celery** конфигурацию (`tasks/`, echo/heartbeat)
7. **🔐 Реализовать JWT** аутентификацию
8. **🔗 Реализовать API endpoints:**
   - `POST /api/auth/login` — аутентификация
   - `GET /api/health` — проверка системы
   - `GET /api/version` — информация о версии
   - `POST /api/tasks/echo` — создание задач
   - `GET /api/tasks/status` — статус задач
9. **🧪 Написать тесты** `pytest` для health и echo

---

## ⚛️ Этап 2. Frontend

### ✅ Задачи:

1. **⚡ Инициализировать Vite** + React + TypeScript
2. **🧹 Настроить линтеры** ESLint + Prettier + strict TS
3. **🏗️ Создать архитектуру FSD-lite:**
   - `shared/` — общие компоненты и утилиты
   - `entities/` — бизнес-сущности  
   - `features/` — функциональности
   - `pages/` — страницы приложения
   - `widgets/` — композитные компоненты
   - `app/` — инициализация приложения
4. **🛣️ Добавить централизованный** `routes.ts`
5. **🌐 Настроить i18n JSON** (минимум 2 языка)
6. **🔗 Реализовать API-клиент** (`shared/lib/api.ts`)
7. **📄 Создать страницы:**
   - **Login** — вход через API
   - **Dashboard** — health-check системы
8. **🧪 Добавить тесты:**
   - **Unit/Component** тесты (Vitest + RTL)
   - **E2E smoke-тест** (Playwright: login → dashboard)

---

## 🛠️ Этап 3. Dev Experience

### ✅ Задачи:

1. **🐳 Добавить docker-compose.yml** для Postgres и Redis
2. **🔧 Написать Makefile** с командами:
   - `make dev` — запуск всех сервисов
   - `make lint` — проверка кода
   - `make test` — запуск тестов  
   - `make migrate` — миграции БД
3. **🔄 Настроить CI (GitHub Actions):**
   - **🐘 Сервис PostgreSQL** для тестов
   - **🔧 Backend:** lint + pytest
   - **⚛️ Frontend:** lint + vitest
   - **🎭 E2E:** playwright тесты
4. **🔍 Проверить end-to-end:** login → dashboard → echo-task

---

## ✅ Этап 4. Завершение

### ✅ Задачи финальной проверки:

1. **🧪 Проверить `make dev`** на чистом окружении
2. **🧹 Проверить `make lint && make test`** — все должно проходить
3. **⚛️ Убедиться в соответствии правилам фронтенда:**
   - i18n JSON ✓
   - TanStack Query ✓  
   - shadcn/ui принципы ✓
4. **🔒 Проверить защиту main ветки:** PR merge возможен только при зелёных проверках
5. **📖 Обновить README.md** с актуальными инструкциями

---

## 📚 Этап 5. Инструкция

### ✅ Задача:

1. **📋 Создать подробную инструкцию:**
   - Как пользоваться бойлерплейтом
   - Где и что изменить для нового проекта  
   - Как настроить окружение разработки
   - Примеры кастомизации под конкретные задачи