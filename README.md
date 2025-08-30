# 🚀 Django + React + TypeScript Boilerplate

Минималистичный, но полный boilerplate для создания современных веб-приложений.

## 🎯 Что включено

- **Backend**: Django + DRF + Celery (Redis, PostgreSQL)
- **Frontend**: Vite + React + TypeScript
- **Аутентификация**: JWT токены
- **Dev Tools**: uv, OrbStack, Makefile
- **CI/CD**: GitHub Actions

## 📋 Требования

- Python 3.11+
- Node.js 20+
- uv (Python package manager)
- Docker (для PostgreSQL и Redis)

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
# Клонируйте репозиторий
git clone <your-repo-url>
cd boilerplate_drf_celery_react_ts

# Запустите базы данных
make docker-up

# Установите зависимости и мигрируйте
make install
make migrate
```

### 2. Запуск в режиме разработки

```bash
# Запуск всех сервисов
make dev
```

Это запустит:
- Backend на http://localhost:8000
- Frontend на http://localhost:5173  
- Celery worker для фоновых задач

### 3. Проверка работы

Откройте http://localhost:5173 в браузере:
1. Войдите в систему (любые данные)
2. Увидите Dashboard с health-check
3. Протестируйте Celery задачи

## 📁 Структура проекта

```
boilerplate/
├── backend/           # Django + DRF + Celery
│   ├── app/
│   │   ├── api/       # REST API endpoints
│   │   ├── core/      # Утилиты и сервисы
│   │   ├── settings/  # Конфигурация Django
│   │   └── tasks/     # Celery задачи
│   └── manage.py
├── frontend/          # React + TypeScript
│   ├── src/
│   │   ├── pages/     # Страницы приложения
│   │   └── lib/       # API клиент и утилиты
│   └── vite.config.ts
├── docker-compose.yml # PostgreSQL + Redis
├── Makefile          # Команды для разработки
└── .github/workflows/ # CI/CD
```

## 🛠 Доступные команды

```bash
# Разработка
make dev              # Запуск всех сервисов
make docker-up        # Запуск PostgreSQL и Redis
make docker-down      # Остановка контейнеров

# Установка и миграции
make install          # Установка зависимостей
make migrate          # Применение миграций Django

# Линтеры и тесты
make lint             # Проверка кода (ruff, eslint, tsc)
make test             # Запуск тестов (pytest, vitest)
make format           # Форматирование кода

# Очистка
make clean            # Очистка временных файлов
```

## 🔧 API Endpoints

- `POST /api/auth/login/` - Аутентификация
- `GET /api/health/` - Проверка состояния системы
- `GET /api/version/` - Версия API
- `POST /api/tasks/echo/` - Создание Celery задачи
- `GET /api/tasks/status/?task_id=...` - Статус задачи

## 🌍 Переменные окружения

### Backend (.env)
```bash
DJANGO_SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/boilerplate
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

### Frontend (.env.local)
```bash
VITE_API_BASE=http://localhost:8000
```

## 🧪 Тестирование

```bash
# Все тесты
make test

# Только backend
cd backend && uv run pytest

# Только frontend  
cd frontend && npm test
```

## 📦 Деплой

Проект готов для деплоя на:
- **Backend**: Railway, Render, DigitalOcean
- **Frontend**: Vercel, Netlify
- **База данных**: Supabase, PlanetScale

См. файлы конфигурации в `backend/app/settings/prod.py`

## 🤝 Разработка

1. Форкните репозиторий
2. Создайте ветку для фичи
3. Запустите `make lint` и `make test` перед коммитом
4. Создайте Pull Request

## 📄 Лицензия

MIT License
