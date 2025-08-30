# 🏗️ Django + React + TypeScript Boilerplate

![CI Status](https://img.shields.io/github/actions/workflow/status/yourusername/boilerplate/ci.yml?branch=main&label=CI&logo=github)
![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Django](https://img.shields.io/badge/Django-5.1-green?logo=django)
![React](https://img.shields.io/badge/React-19-blue?logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5.8-blue?logo=typescript)
![License](https://img.shields.io/badge/License-MIT-yellow)

**Профессиональный, готовый к продакшену бойлерплейт** для современных web-приложений с Django + DRF + Celery бэкендом и React + TypeScript фронтендом.

---

## ✨ Особенности

### 🔧 Backend
- **Django 5.1** + **DRF** для мощного API
- **Celery** + **Redis** для фоновых задач
- **PostgreSQL** для надежного хранения данных
- **JWT Authentication** с автообновлением токенов
- **Полное покрытие тестами** (pytest + factory-boy)
- **Готовые health-check** эндпоинты

### ⚛️ Frontend
- **React 19** с **TypeScript** и **Vite**
- **FSD-lite архитектура** для масштабируемости
- **TanStack Query** + **Zustand** для state management
- **Tailwind CSS** + **GitHub Primer** дизайн система
- **Интернационализация** (i18n) из коробки
- **Dark/Light тема** с системной поддержкой
- **E2E тесты** с Playwright

### 🛠️ DevX & CI/CD
- **Makefile** с удобными командами разработки
- **GitHub Actions** с матричным тестированием
- **Dependabot** для автообновления зависимостей
- **Security сканирование** (CodeQL + GitLeaks)
- **Docker** окружение для разработки
- **Полная типизация** TypeScript + mypy

---

## 🚀 Быстрый старт

### 📋 Требования

- **Python 3.11+** 
- **Node.js 18+**
- **Docker** и **Docker Compose**
- **uv** - `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **pnpm** - `npm install -g pnpm`

### ⚡ Запуск за 1 минуту

```bash
# 1. Клонируйте и войдите в проект
git clone <your-boilerplate-repo>
cd boilerplate_drf_celery_react_ts

# 2. Один comando для запуска всего!
make start

# 3. В новых терминалах запустите разработку
make dev
```

**Готово!** 🎉 
- **API**: http://localhost:8000
- **Frontend**: http://localhost:5173  
- **Admin**: http://localhost:8000/admin

### 📱 Первый вход
- **Username**: `admin`
- **Password**: `admin123`

---

## 🏗️ Архитектура

<details>
<summary>🔧 Backend Architecture</summary>

```
backend/
├── app/
│   ├── settings/           # 🔧 Конфигурация
│   │   ├── base.py        # Общие настройки
│   │   ├── local.py       # Локальная разработка
│   │   └── prod.py        # Продакшн
│   ├── api/               # 🌐 API endpoints
│   │   ├── views.py       # ViewSets
│   │   ├── serializers.py # Сериализаторы
│   │   └── urls.py        # URL routing
│   ├── tasks/             # 📋 Celery задачи
│   │   └── tasks.py       # Background jobs
│   └── core/              # 🛠️ Утилиты и хелперы
└── tests/                 # 🧪 Тесты (100% coverage)
```

**Технологии:**
- Django 5.1 + DRF для REST API
- Celery + Redis для async задач
- PostgreSQL для данных
- JWT для аутентификации
- pytest + factory-boy для тестов

</details>

<details>
<summary>⚛️ Frontend Architecture</summary>

```
frontend/src/
├── app/                   # 🚀 Application layer
│   ├── providers/         # React providers
│   └── routes/           # Routing + guards
├── shared/               # 🔗 Shared resources
│   ├── ui/              # UI components
│   ├── lib/             # Utilities + API
│   └── config/          # Constants + types
├── entities/            # 📊 Business entities
│   ├── user/           # User model + API
│   └── task/           # Task model + API
├── features/           # ✨ Feature components
│   ├── auth/          # Authentication
│   └── dashboard/     # Dashboard functionality
└── pages/             # 📄 Page components
    ├── login/         # Login page
    └── dashboard/     # Dashboard page
```

**Технологии:**
- React 19 с TypeScript
- FSD-lite архитектура
- TanStack Query + Zustand
- Tailwind CSS + GitHub Primer
- Vitest + Testing Library + Playwright

</details>

---

## 🛠️ Команды разработки

Все команды доступны через **Makefile**:

```bash
# 🚀 Основные команды
make dev                 # Запуск всех сервисов разработки
make setup              # Первоначальная настройка проекта
make test               # Запуск всех тестов
make lint               # Проверка кода линтерами

# 🐳 Docker сервисы
make services           # Запуск PostgreSQL + Redis
make services-with-tools # + pgAdmin + Redis Commander
make docker-down        # Остановка всех сервисов

# 🗄️ База данных
make migrate            # Применить миграции
make makemigrations     # Создать миграции
make superuser          # Создать суперпользователя

# 🧪 Тестирование
make backend-test       # Backend тесты (pytest)
make frontend-test      # Frontend тесты (vitest)
make e2e               # E2E тесты (playwright)
make test-coverage     # Тесты с покрытием

# 🧹 Качество кода
make backend-lint       # Backend: ruff + mypy
make frontend-lint      # Frontend: eslint + prettier + tsc
make backend-fix        # Исправить форматирование backend
make frontend-fix       # Исправить форматирование frontend

# 🔧 Утилиты
make health            # Проверка health API
make status            # Статус Docker сервисов
make logs              # Просмотр логов
make clean             # Очистка кэшей и временных файлов

# 📖 Помощь
make help              # Показать все команды
```

---

## 🔗 API Reference

### Authentication
- `POST /api/auth/login/` - Аутентификация пользователя
- `GET /api/auth/profile/` - Профиль пользователя  
- `POST /api/auth/logout/` - Выход из системы

### System
- `GET /api/health/` - Health check (DB + Redis + Celery)
- `GET /api/version/` - Информация о версии API
- `GET /` - API информация и маршруты

### Tasks  
- `POST /api/tasks/echo/` - Создать echo задачу
- `POST /api/tasks/heartbeat/` - Создать heartbeat задачу
- `GET /api/tasks/status/` - Статус задачи по ID

<details>
<summary>📋 Примеры запросов</summary>

```bash
# Логин
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Health check
curl http://localhost:8000/api/health/

# Создание задачи
curl -X POST http://localhost:8000/api/tasks/echo/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello World", "delay": 5}'
```

</details>

---

## 🧪 Тестирование

### Backend Tests (pytest)
```bash
make backend-test       # Все тесты
make test-coverage      # С покрытием

# Специфичные тесты
cd backend
uv run pytest tests/test_api.py -v
uv run pytest tests/test_auth.py::TestJWTTokens -v
```

### Frontend Tests  
```bash
make frontend-test      # Unit тесты (vitest)
make e2e               # E2E тесты (playwright)

# В watch режиме
cd frontend
pnpm test              # Watch режим
pnpm e2e:ui            # E2E с UI
```

### Структура тестов

**Backend (pytest):**
- ✅ API endpoints тестирование
- ✅ Authentication & JWT flows  
- ✅ Celery задачи
- ✅ Database модели
- ✅ Permissions & security

**Frontend (vitest + RTL):**
- ✅ Component тестирование
- ✅ API интеграция (mocked)
- ✅ State management (stores)
- ✅ Routing & navigation

**E2E (Playwright):**
- ✅ Login flow
- ✅ Dashboard navigation
- ✅ Task creation & polling
- ✅ Theme switching
- ✅ Responsive design

---

## 🚀 Подготовка к продакшену

### 1. 📝 Адаптация под ваш проект

```bash
# Полное руководство по адаптации
cat docs/ADAPTATION_GUIDE.md

# Основные шаги:
# 1. Переименовать проект
# 2. Настроить переменные окружения  
# 3. Обновить домены и CORS
# 4. Настроить production DB
```

### 2. 🌐 Переменные окружения

**Backend (.env):**
```bash
DJANGO_SECRET_KEY=your-super-secure-key
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
ALLOWED_HOSTS=your-domain.com,api.your-domain.com
CORS_ALLOWED_ORIGINS=https://your-domain.com
```

**Frontend (.env):**
```bash
VITE_API_BASE=https://api.your-domain.com
VITE_ENVIRONMENT=production
```

### 3. 🏗️ Сборка для продакшена

```bash
# Backend
cd backend
uv run python manage.py collectstatic
uv run python manage.py migrate --settings=app.settings.prod

# Frontend  
cd frontend
pnpm build
```

### 4. 🐳 Docker Production

```dockerfile
# Добавьте production Dockerfiles
# backend/Dockerfile.prod
# frontend/Dockerfile.prod  
# docker-compose.prod.yml
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions включает:

- ✅ **Matrix testing**: Python 3.11/3.12, Node 18/20/22
- ✅ **Multi-OS**: Ubuntu, macOS, Windows
- ✅ **Code quality**: ESLint, Prettier, Ruff, mypy
- ✅ **Security scanning**: CodeQL, GitLeaks, dependency audit
- ✅ **E2E testing**: Full application flow
- ✅ **Coverage reports**: Codecov integration
- ✅ **Auto-dependency updates**: Dependabot

### Workflow triggers:
- **Push** to `main`/`develop`
- **Pull Requests** to `main`
- **Schedule**: Security scans weekly
- **Manual dispatch**: On-demand testing

### Security Features:
- 🔒 Secret scanning with GitLeaks
- 🛡️ CodeQL static analysis  
- 📦 Dependency vulnerability checks
- 🤖 Automated security updates

---

## 📊 Производительность

### Backend
- ⚡ **Django ORM** оптимизация
- 🔄 **Redis caching** для частых запросов
- 📊 **Database indexing** для быстрых запросов
- 🔧 **Connection pooling** для эффективности

### Frontend  
- ⚡ **Vite** для мгновенной пересборки
- 📦 **Code splitting** по маршрутам
- 🗂️ **TanStack Query** кэширование
- 🎨 **Tailwind** purging для минимального CSS

### Мониторинг
- 📈 **Health checks** для всех сервисов
- 🚨 **Error tracking** готов для Sentry
- 📊 **Performance metrics** endpoints
- 🔍 **Structured logging** для debugging

---

## 📚 Документация

### Основная документация:
- 📖 **[Описание архитектуры](docs/boilerplate-description.md)**
- 📋 **[План разработки](docs/boilerplate-tasks.md)**  
- 🚀 **[Руководство по адаптации](docs/ADAPTATION_GUIDE.md)**

### Внешние ресурсы:
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [TanStack Query](https://tanstack.com/query/)

---

## 🤝 Contributing

Мы приветствуем вклад в развитие проекта!

### Процесс:
1. 🍴 **Fork** репозитория
2. 🌿 Создайте **feature branch**
3. ✅ Убедитесь что **все тесты проходят**
4. 📝 Добавьте **тесты** для новой функциональности
5. 🔧 Запустите **линтеры**: `make lint`
6. 📤 Создайте **Pull Request**

### Правила:
- ✅ Все PR должны проходить CI
- 📝 Код должен быть документирован  
- 🧪 Новый функционал должен иметь тесты
- 🎨 Следуйте code style проекта

---

## 🆘 Поддержка

### 💬 Получить помощь:
- 📖 Проверьте **[документацию](docs/)**
- 🐛 Создайте **[Issue](issues/new)** для багов
- 💡 Предложите **[Enhancement](issues/new)** для идей
- 💬 Обсуждение в **[Discussions](discussions/)**

### 🔗 Полезные ссылки:
- [Django Discord](https://discord.gg/xcRH6mN4fa)
- [Reactiflux Discord](https://discord.gg/reactiflux)

---

## 📄 License

Этот проект распространяется под **MIT License** - см. файл [LICENSE](LICENSE) для подробностей.

---

## 🎯 Roadmap

### 🚀 v1.1 (Планируется)
- [ ] **GraphQL** поддержка (опциональная)
- [ ] **WebSocket** real-time возможности
- [ ] **Multi-tenancy** поддержка
- [ ] **API documentation** с OpenAPI/Swagger
- [ ] **Performance monitoring** dashboard

### 🎨 v1.2 (Будущее)
- [ ] **Микросервисы** архитектура (опциональная)
- [ ] **Kubernetes** deployment manifests  
- [ ] **Mobile app** React Native boilerplate
- [ ] **Admin dashboard** с React Admin

---

## ⭐ Поставьте звезду!

Если этот проект помог вам - поставьте **⭐ звезду** на GitHub!

**Happy coding!** 🚀✨