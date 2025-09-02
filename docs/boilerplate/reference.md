# 📚 Справочники

> **Цель:** Быстро найти нужную информацию о проекте, командах и конфигурации.

---

## 📁 **Структура проекта**

```
your-project/
├── backend/                    # Django + DRF + Celery
│   ├── your_project/          # Основной Django модуль
│   │   ├── settings/          # Настройки (local, prod, migrate)
│   │   ├── api/              # DRF эндпоинты
│   │   ├── core/             # Django apps
│   │   │   └── management/commands/  # Кастомные команды
│   │   ├── tasks/            # Celery задачи
│   │   └── urls.py           # URL маршруты
│   ├── Dockerfile            # Образ для Cloud Run
│   ├── worker_entrypoint.py  # Энтрипойнт для Celery worker
│   └── pyproject.toml        # Python зависимости (uv)
│
├── frontend/                   # React + TypeScript + Vite
│   ├── src/
│   │   ├── app/              # Роутинг и провайдеры
│   │   ├── entities/         # Бизнес-логика (User, Task)
│   │   ├── features/         # Фичи (Auth, Dashboard)
│   │   ├── pages/            # Страницы
│   │   ├── shared/           # Переиспользуемые компоненты
│   │   └── locales/          # i18n переводы
│   └── package.json          # Node.js зависимости
│
├── ops/                       # GCP конфигурация
│   ├── urlmap-config.yaml    # Load Balancer маршруты
│   └── http-redirect-config.yaml  # HTTP → HTTPS redirect
│
├── docs/
│   ├── boilerplate/          # 📋 Эта документация
│   └── infra/               # Описание инфраструктуры
│
├── .github/workflows/        # GitHub Actions CI/CD
│   ├── ci.yml               # Тесты и проверки качества
│   ├── deploy-backend.yml   # Деплой Django + Celery
│   └── deploy-frontend.yml  # Деплой React в Cloud Storage
│
├── docker-compose.yml        # Локальная разработка
├── Makefile                 # Команды для разработки
├── env.example              # Пример переменных окружения
└── README.md               # Основная документация
```

---

## ⚡ **Make команды**

### Локальная разработка:
```bash
make start              # Запуск всех сервисов
make stop               # Остановка всех сервисов  
make restart            # Перезапуск всех сервисов
make clean              # Очистка Docker volumes/images
```

### Backend команды:
```bash
make shell-backend      # Django shell
make migrate            # Применить миграции
make collectstatic      # Собрать статические файлы
make createsuperuser    # Создать суперпользователя
make logs-backend       # Логи Django
make logs-worker        # Логи Celery worker
```

### Frontend команды:
```bash
make shell-frontend     # Bash в frontend контейнере
make logs-frontend      # Логи Vite dev server
```

### Тестирование:
```bash
make test               # Все тесты
make test-backend       # Backend тесты
make test-frontend      # Frontend тесты  
make test-e2e          # End-to-end тесты
make pre-commit        # Полная проверка качества кода
```

### Database:
```bash
make db-shell          # Подключиться к PostgreSQL
make db-reset          # Пересоздать БД (⚠️ удаляет все данные)
make clean-db          # Очистить только данные
```

### Docker:
```bash
make build             # Пересобрать все образы
make logs              # Логи всех сервисов
```

---

## 🔐 **Переменные окружения**

### Backend (.env):
```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
DEBUG=true
DJANGO_SETTINGS_MODULE=your_project.settings.local

# Database  
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/your_project_db
DB_HOST=localhost
DB_NAME=your_project_db
DB_USER=postgres
DB_PASSWORD=postgres

# Redis & Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Encryption
ENCRYPTION_KEY=your-fernet-key

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Frontend (.env.local):
```bash
VITE_API_BASE=http://localhost:8000
VITE_APP_NAME=Your Project Name
VITE_ENVIRONMENT=development  
VITE_DEBUG=true
```

### Production переменные (GCP Secrets):
```bash
DJANGO_SECRET_KEY        # Django secret key
ENCRYPTION_KEY           # Fernet encryption key
DB_HOST                  # Cloud SQL socket path
DB_NAME                  # PostgreSQL database name
DB_USER                  # PostgreSQL username  
DB_PASSWORD              # PostgreSQL password
REDIS_URL                # Upstash Redis URL
CORS_ALLOWED_ORIGINS     # Allowed frontend origins
```

---

## 🌐 **API эндпоинты**

### System endpoints:
```bash
GET  /                   # API info
GET  /api/health/        # Health check
GET  /api/version/       # Version info
GET  /nukoadmin/         # Django admin (скрыт в prod)
```

### Authentication:
```bash
POST /api/auth/login/    # JWT login
GET  /api/auth/profile/  # User profile (требует JWT)
```

### Task management:
```bash
POST /api/tasks/echo/      # Создать echo задачу
POST /api/tasks/heartbeat/ # Создать heartbeat задачу  
POST /api/tasks/long/      # Создать долгую задачу
GET  /api/tasks/status/    # Статус задачи по ID
GET  /api/tasks/list/      # Список задач пользователя
```

### Примеры запросов:
```bash
# Health check
curl https://api.your-domain.com/api/health/

# Login  
curl -X POST https://api.your-domain.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "<USERNAME>", "password": "<PASSWORD>"}'

# Create task (с JWT токеном)
curl -X POST https://api.your-domain.com/api/tasks/echo/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -d '{"message": "Hello World"}'
```

---

## 🔧 **Конфигурация сервисов**

### Django настройки:
- **local.py:** Локальная разработка (SQLite, Debug=True)
- **prod.py:** Production (Cloud SQL, Debug=False)  
- **migrate.py:** Только для миграций в Cloud Run Job

### Celery worker:
- **worker_entrypoint.py:** HTTP wrapper для Cloud Run Service
- **Health check:** GET /health возвращает статус worker'а
- **Graceful shutdown:** Обрабатывает SIGTERM/SIGINT

### Load Balancer (urlmap-config.yaml):
```yaml
# Static assets: /assets/* → прямо из bucket
# Root files: /, /index.html → bucket  
# SPA routes: остальные → redirect на / (для client-side routing)
```

---

## 🎯 **GitHub Actions workflows**

### CI Pipeline (.github/workflows/ci.yml):
- **Триггеры:** Push в main/develop, PR в main
- **Проверки:** Lint, format, type checking, tests
- **Матрица:** Python 3.11/3.12, Node 18/20/22
- **E2E тесты:** Playwright (можно включить/отключить)

### Backend Deploy (.github/workflows/deploy-backend.yml):
- **Триггеры:** Git tags `v*` (v1.0.0, v1.0.1, etc)
- **Шаги:**
  1. Build Docker image
  2. Push to Artifact Registry  
  3. **Run DB migrations** (migrate-v1-0-0 job)
  4. Deploy API service
  5. Deploy Celery Worker
  6. Health checks

### Frontend Deploy (.github/workflows/deploy-frontend.yml):
- **Триггеры:** Git tags `v*`
- **Шаги:**
  1. Build React SPA
  2. Upload to Cloud Storage
  3. Set cache headers
  4. Invalidate CDN cache
  5. Health checks

---

## 🐛 **Отладка и логи**

### Локальная отладка:
```bash
# Логи конкретного сервиса
docker-compose logs -f backend
docker-compose logs -f worker  
docker-compose logs -f frontend

# Подключиться к контейнеру
docker-compose exec backend bash
docker-compose exec frontend bash
```

### Production логи:
```bash
# Cloud Run сервисы
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=your-project-api" --limit=100

gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=your-project-worker" --limit=100

# Cloud Run Jobs (миграции)
gcloud logging read "resource.type=cloud_run_job" --limit=50
```

### Health checks:
```bash
# API health
curl https://api.your-domain.com/api/health/

# Celery worker health (в Cloud Run worker'е)
curl https://your-project-worker-url.run.app/health
```

---

## 🔄 **Версионирование и деплой**

### Semantic Versioning:
```bash
v1.0.0    # Major.Minor.Patch
v1.0.1    # Bug fixes
v1.1.0    # New features
v2.0.0    # Breaking changes
```

### Создание релиза:
```bash
# Создай и запуши тег
git tag v1.0.1
git push origin v1.0.1

# Автоматически запустится деплой
# Наблюдай в GitHub Actions
```

### Rollback:
```bash
# Откат Cloud Run сервисов
gcloud run services update-traffic your-project-api \
  --to-revisions=LATEST=100 --region=asia-southeast1

# Или передеплой предыдущего тега  
git tag -d v1.0.1
git push origin --delete v1.0.1
git tag v1.0.0  # Предыдущая версия
git push origin v1.0.0
```

---

## 💡 **Полезные команды**

### GCP проверки:
```bash
# Cloud Run сервисы
gcloud run services list --region=asia-southeast1

# SSL сертификаты  
gcloud compute ssl-certificates list --global

# Load Balancer
gcloud compute forwarding-rules list --global

# Секреты
gcloud secrets list
```

### Мониторинг:
```bash
# Cloud SQL
gcloud sql instances list

# Cloud Storage  
gsutil ls gs://app.your-domain.com/

# Artifact Registry
gcloud artifacts repositories list --location=asia-southeast1
```

---

## 📞 **Поддержка**

### Если что-то сломалось:
1. **Проверь логи** - сначала локально, потом в GCP  
2. **GitHub Actions** - посмотри логи failed workflow
3. **Health checks** - API должен отвечать на /api/health/
4. **DNS propagation** - `dig your-domain.com`
5. **SSL status** - `gcloud compute ssl-certificates list`

### Полезные ссылки:
- **GitHub Actions:** https://github.com/your-username/your-project/actions
- **GCP Console:** https://console.cloud.google.com
- **Cloud Run:** https://console.cloud.google.com/run
- **Cloud SQL:** https://console.cloud.google.com/sql

---

## 🎉 **Готово!**

Теперь у тебя есть полная документация для создания production-ready проектов на основе этого boilerplate. 

**Удачи в разработке! 🚀**
