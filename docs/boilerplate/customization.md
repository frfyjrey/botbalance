# 🔧 Адаптация под новый проект

> **Цель:** Переименовать botbalance → your-project и настроить под твой домен.

## 📋 **Что нужно изменить:**
- ✅ Название проекта во всех файлах
- ✅ Домены: `botbalance.me` → `your-domain.com` 
- ✅ GitHub репозиторий
- ✅ База данных и сервисы
- ✅ Docker образы и теги

## 🚀 **ВАЖНО: Порядок действий критичен!**
> Следуй строго по шагам - мы прошли все грабли за тебя.

---

## 📝 **Шаг 1: Переименование проекта**

### 1.1. Django Backend:
```bash
# Переименуй основной модуль:
mv backend/botbalance backend/YOUR_PROJECT_NAME

# В файле backend/manage.py измени:
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'YOUR_PROJECT_NAME.settings.local')

# В backend/pyproject.toml измени:
name = "your-project-backend" 

# В backend/YOUR_PROJECT_NAME/asgi.py и wsgi.py:
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'YOUR_PROJECT_NAME.settings.local')
application = get_asgi_application()
```

### 1.2. Обнови все импорты:
```bash
# Найди и замени во ВСЕХ файлах backend/:
grep -r "botbalance" backend/ --exclude-dir=.git

# Замени botbalance на your_project_name в:
# - settings/*.py
# - urls.py  
# - apps.py
# - все Django импорты
```

### 1.3. Frontend:
```bash
# В frontend/package.json:
"name": "your-project-frontend"

# В frontend/index.html:  
<title>Your Project Name</title>

# В frontend/src/shared/config/constants.ts:
export const APP_NAME = 'Your Project Name'
```

---

## 🌐 **Шаг 2: Смена доменов**

### 2.1. Backend домены:
```bash
# В backend/botbalance/settings/prod.py:
ALLOWED_HOSTS = ["api.YOUR_DOMAIN.com", "YOUR_PROJECT-api-*.run.app"]
CORS_ALLOWED_ORIGINS = ["https://app.YOUR_DOMAIN.com"]

# В backend/botbalance/urls.py root_view():
"name": "Your Project API"
```

### 2.2. Frontend домены:
```bash
# В frontend/.env.production:  
VITE_API_BASE=https://api.YOUR_DOMAIN.com
VITE_APP_NAME=Your Project Name

# В frontend/.env.example:
VITE_API_BASE=https://api.YOUR_DOMAIN.com
```

### 2.3. Инфраструктура:
```bash
# В ops/urlmap-config.yaml:
hosts:
- app.YOUR_DOMAIN.com

# В .github/workflows/deploy-frontend.yml:
BUCKET_NAME: app.YOUR_DOMAIN.com

# В всех docs/infra/*.md:
# Замени все botbalance.me на YOUR_DOMAIN.com
```

---

## 🔀 **Шаг 3: GitHub репозиторий**

### 3.1. Создай новый репо:
```bash
# В GitHub создай новый приватный репозиторий
# Название: your-project

# Обнови remote:
git remote set-url origin https://github.com/YOUR_USERNAME/your-project.git
```

### 3.2. Обнови README.md:
```markdown
# Your Project Name

> Django + React production-ready boilerplate

## Quick Start
See [docs/boilerplate/quick-start.md](docs/boilerplate/quick-start.md)
```

---

## ☁️ **Шаг 4: GCP проект**

### 4.1. Создай GCP проект:
```bash
# В Google Cloud Console создай новый проект
PROJECT_ID="your-project-prod"  # Без дефисов, только lowercase

# Обнови в GitHub Actions workflows:
# .github/workflows/deploy-backend.yml:
env:
  PROJECT_ID: your-project-prod
  AR_REPO: your-project-backend
  SERVICE_API: your-project-api
  SERVICE_WORKER: your-project-worker
```

### 4.2. Обнови инфраструктуру:
```bash
# В docs/infra/infrastructure-tasks.md замени:
PROJECT_ID="your-project-prod"
FRONTEND_BUCKET="gs://app.YOUR_DOMAIN.com" 
```

---

## 🗃️ **Шаг 5: База данных и сервисы**

### 5.1. PostgreSQL:
```bash
# В Docker Compose и env файлах:  
POSTGRES_DB=your_project_db
DB_NAME=your_project_db

# В GCP Cloud SQL:
# Создай инстанс: your-project-pg
# База: your_project_db  
```

### 5.2. Celery и Redis:
```bash
# Upstash Redis:
# Создай новую базу для проекта
# Обнови REDIS_URL в секретах
```

---

## 🐳 **Шаг 6: Docker образы**

### 6.1. Registry и tags:
```bash
# В .github/workflows/deploy-backend.yml:
AR_REPO: your-project-backend

# Образы будут: 
# your-project-backend/api:v1.0.0
# your-project-backend/worker:v1.0.0
```

---

## ⚠️ **КРИТИЧНЫЕ ГРАБЛИ (которые мы прошли):**

### 🚨 **1. Cloud Run Job naming**
**ОШИБКА:** `migrate-v1.0.0` содержит точки  
**РЕШЕНИЕ:** Уже исправлено в workflow - используется `sed 's/\./-/g'`

### 🚨 **2. Cloud Run Service tags**  
**ОШИБКА:** `--tag=v1.0.0` содержит точки
**РЕШЕНИЕ:** Уже исправлено в workflow - используется `sed 's/\./-/g'`

### 🚨 **3. IAM роли GitHub Actions**
**НУЖНЫ ВСЕ роли:**
- `roles/run.admin`
- `roles/storage.admin` 
- `roles/artifactregistry.admin`
- `roles/cloudsql.client`
- `roles/secretmanager.secretAccessor`
- `roles/iam.serviceAccountUser` ⚠️ **КРИТИЧНО - без этого миграции не работают**

### 🚨 **4. Django settings split**
**ПРОБЛЕМА:** Один prod.py для всего  
**РЕШЕНИЕ:** Создан migrate.py отдельно для миграций

### 🚨 **5. Admin URL exposure**
**ПРОБЛЕМА:** Админка показывается в API root в продакшене
**РЕШЕНИЕ:** Динамический показ только при DEBUG=True

---

## ✅ **Проверь что все переименовал:**

```bash
# Не должно остаться упоминаний botbalance:
grep -r "botbalance" . --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=dist

# Не должно остаться .me доменов:
grep -r "\.me" . --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=dist
```

---

## 🎯 **Готов к деплою!**
После всех изменений проверь локальный запуск и переходи к деплою.

**Следующий шаг:** [Production деплой](deployment.md)
