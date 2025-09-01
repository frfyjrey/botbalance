# 🏗️ BotBalance

Web-приложение на Django + React + TypeScript с Celery для фоновых задач.

---

## 🔧 Стек технологий

### Backend
- Django 5.1 + DRF
- Celery + Redis
- PostgreSQL
- JWT Authentication
- pytest для тестов

### Frontend
- React + TypeScript + Vite
- TanStack Query + Zustand
- Tailwind CSS
- i18n поддержка
- Playwright E2E тесты

---

## 🚀 Запуск

### Требования
- Python 3.11+
- Node.js 18+
- Docker и Docker Compose
- uv - `curl -LsSf https://astral.sh/uv/install.sh | sh`
- pnpm - `npm install -g pnpm`

### Команды
```bash
# Запуск сервисов (PostgreSQL, Redis)
make start

# Запуск разработки
make dev
```

**Доступ:**
- API: http://localhost:8000
- Frontend: http://localhost:5173
- Admin: http://localhost:8000/nukoadmin (admin/admin123)

---

## 🏗️ Структура

### Backend
```
backend/
├── botbalance/
│   ├── settings/          # Конфигурация
│   ├── api/              # API endpoints
│   ├── tasks/            # Celery задачи
│   └── core/             # Утилиты
└── tests/                # Тесты
```

### Frontend  
```
frontend/src/
├── app/                  # Application layer
├── shared/              # UI components, утилиты
├── entities/            # Business entities
├── features/            # Функциональности  
└── pages/              # Страницы
```

---

## 🛠️ Команды разработки

```bash
# Основные
make dev                 # Запуск разработки
make test               # Все тесты
make lint               # Линтеры

# Docker
make start              # Запуск PostgreSQL + Redis
make stop               # Остановка сервисов

# База данных
make migrate            # Применить миграции
make superuser          # Создать суперпользователя

# Тесты
make backend-test       # Backend тесты
make frontend-test      # Frontend тесты
make e2e               # E2E тесты

# Линтеры
make backend-lint       # Backend: ruff + mypy
make frontend-lint      # Frontend: eslint + tsc
make backend-fix        # Автоисправление backend
make frontend-fix       # Автоисправление frontend
```

---

## 🔗 API

### Authentication
- `POST /api/auth/login/` - Логин
- `GET /api/auth/profile/` - Профиль пользователя

### System
- `GET /api/health/` - Health check
- `GET /api/version/` - Версия API

### Tasks
- `POST /api/tasks/echo/` - Создать echo задачу
- `GET /api/tasks/status/` - Статус задачи

---

## 🧪 Тестирование

```bash
# Backend тесты
make backend-test       # pytest
cd backend && uv run pytest tests/ -v

# Frontend тесты  
make frontend-test      # vitest
make e2e               # playwright

# В watch режиме
cd frontend && pnpm test
```

### Покрытие
- **Backend**: API, auth, Celery задачи
- **Frontend**: компоненты, state management
- **E2E**: полный пользовательский flow

---

## 🌐 Переменные окружения

### Backend (.env)
```bash
DJANGO_SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
ALLOWED_HOSTS=your-domain.com
CORS_ALLOWED_ORIGINS=https://your-domain.com
```

### Frontend (.env)
```bash
VITE_API_BASE=https://api.your-domain.com
VITE_ENVIRONMENT=production
```