# 🏗️ Boilerplate Description

## 🎯 Цель

Создать **минималистичный**, но **строгий** boilerplate-проект для приложений с DRF-бэкендом и фронтендом на Vite + React + TypeScript.

### 📋 Проект сразу должен соответствовать установленным правилам:

- **🔧 Бэкенд** → Django + DRF + Celery (с Redis и Postgres)
- **⚛️ Фронтенд** → React + TS + Vite, архитектура FSD-lite, i18n JSON, TanStack Query  
- **🛠️ Dev Experience** → OrbStack (docker-compose для Postgres + Redis), единое окружение Python (через uv), Makefile
- **🚀 CI/CD** → GitHub Actions: линтеры, типы, тесты (юнит + e2e)
- **☁️ Деплой** → Проект готов для последующего деплоя на GCP

---

## 📂 Структура репозитория

```
boilerplate/
├── backend/                        # 🔧 Django Backend
│   ├── app/
│   │   ├── settings/
│   │   │   ├── base.py             # Общие настройки
│   │   │   ├── local.py            # Локальная разработка
│   │   │   └── prod.py             # Продакшн
│   │   ├── api/                    # 🔗 DRF views (auth, health, tasks)
│   │   ├── core/                   # 🛠️ Утилиты
│   │   ├── tasks/                  # 📋 Celery tasks (echo, heartbeat)  
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── manage.py
│   └── pyproject.toml              # 📦 Python dependencies
├── frontend/                       # ⚛️ React Frontend
│   ├── src/
│   │   ├── app/                    # 🚀 Инициализация приложения, routes.ts
│   │   ├── shared/                 # 🔗 ui/, lib/, i18n/
│   │   ├── entities/               # 📊 Бизнес-сущности
│   │   ├── features/               # ✨ Фичи
│   │   ├── pages/                  # 📄 Login, Dashboard
│   │   └── widgets/                # 🧩 Виджеты
│   ├── public/
│   ├── package.json
│   └── vite.config.ts              # ⚡ Vite конфигурация
├── ops/
│   └── agent/                      # 🤖 Журнал ИИ-агента
├── docker-compose.yml              # 🐳 Postgres + Redis
├── Makefile                        # 🛠️ Dev команды
├── .github/workflows/ci.yml        # 🔄 CI/CD
└── README.md                       # 📖 Документация
```

---

## 🔧 Backend

### 📚 Технологии
- **Django + DRF** для API
- **Celery + Redis** для фоновых задач  
- **PostgreSQL** как основная БД
- **JWT-аутентификация** (`djangorestframework-simplejwt`)

### 🔗 API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `POST` | `/api/auth/login` | 🔐 Выдача токена |
| `GET` | `/api/health` | 🏥 Проверка DB/Redis |
| `GET` | `/api/version` | 📋 Версия API |
| `POST` | `/api/tasks/echo` | 📝 Создать задачу |
| `GET` | `/api/tasks/status?task_id=...` | 📊 Статус задачи |

### ⚙️ Конфигурация

| Файл | Назначение |
|------|------------|
| `base.py` | 🔧 Общие настройки |
| `local.py` | 🛠️ DEBUG, локальная разработка |
| `prod.py` | 🚀 Прод (Cloud SQL + Upstash) |

### 🔐 Environment Variables

```bash
# Основные настройки
DJANGO_SECRET_KEY=dev-secret
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/boilerplate
REDIS_URL=redis://localhost:6379/0

# Сеть и CORS
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

---

## ⚛️ Frontend

### 📚 Технологии
- **React + TypeScript + Vite** — основной стек
- **Архитектура FSD-lite** — `shared/`, `entities/`, `features/`, `widgets/`, `pages/`, `app/`
- **I18n** — все строки в JSON файлах
- **UI Framework** — Tailwind CSS + shadcn/ui принципы

### 🗂️ Управление состоянием
- **TanStack Query** — для серверных данных  
- **Zustand** — только для UI-состояния
- **Routing** — централизованный `routes.ts`

### 📄 Страницы

| Страница | Описание | Функции |
|----------|----------|---------|
| **Login** | 🔐 Форма входа | Запрос к API, JWT токены |
| **Dashboard** | 📊 Главная панель | Health-check, статус системы |

---

## 🛠️ Dev Experience

### 🐳 Окружение разработки
- **OrbStack/docker-compose** — для Postgres и Redis
- **uv** — для Python-окружения
- **Makefile** — единые команды для разработки

### 🔧 Makefile команды

| Команда | Описание |
|---------|----------|
| `make dev` | 🚀 Запуск api, worker, фронта |
| `make lint` | 🧹 Линтеры для всего кода |
| `make test` | 🧪 Все тесты (unit + e2e) |
| `make migrate` | 📦 Миграции БД |

### 🔄 CI/CD (GitHub Actions)

#### 📋 Проверки при каждом PR:
- **🧹 Линтеры:** `ruff`, `mypy`, `eslint`, `prettier`, `tsc`
- **🧪 Тесты:** `pytest`, `vitest` 
- **🎭 E2E:** `playwright` smoke-тесты

> **⚠️ Важно:** Merge PR возможен только при **зелёных проверках**

---

## 🚦 Definition of Done

### ✅ Критерии готовности:

1. **🚀 Локальный запуск**
   - `make dev` поднимает окружение локально (api, worker, фронт)

2. **🔐 Аутентификация** 
   - Логин работает через API
   - Dashboard показывает health статус

3. **📋 Фоновые задачи**
   - Celery-задачи выполняются и проверяются через API

4. **✅ CI/CD**
   - CI зелёный (линтеры, тесты, e2e)

5. **⚛️ Frontend соответствие**
   - FSD-lite архитектура ✓
   - i18n JSON ✓ 
   - TanStack Query ✓
   - shadcn/ui принципы ✓

6. **📖 Документация**
   - README.md содержит инструкции по запуску