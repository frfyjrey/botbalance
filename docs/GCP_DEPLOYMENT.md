# 🌐 Руководство по деплою на Google Cloud Platform

Пошаговая инструкция по развертыванию Django + React приложения на GCP с использованием Cloud Run, Cloud SQL и Cloud Storage.

---

## 📋 Архитектура деплоя

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │────│   Cloud Storage │    │   Cloud SQL     │
│ (app.domain.com)│    │   (Frontend)    │    │ (PostgreSQL)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       │                       │
┌─────────────────┐              │                       │
│   Cloud Run     │──────────────┼───────────────────────┘
│   (Backend API) │              │
│api.domain.com   │              │
└─────────────────┘              │
         │                       │
         ▼                       │
┌─────────────────┐              │
│   Cloud Storage │──────────────┘
│   (Media files) │
└─────────────────┘
```

---

## 🛠️ Подготовка проекта

### 1. Установка Google Cloud CLI

```bash
# macOS
brew install google-cloud-sdk

# Ubuntu/Debian
sudo apt-get install google-cloud-cli

# Инициализация
gcloud init
gcloud auth application-default login
```

### 2. Создание нового проекта

```bash
# Создать проект
export PROJECT_ID="your-project-id"
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# Включить необходимые API
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

---

## 🗄️ Настройка базы данных (Cloud SQL)

### 1. Создание PostgreSQL инстанса

```bash
# Создать PostgreSQL инстанс
gcloud sql instances create your-app-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=europe-west1 \
    --storage-auto-increase \
    --backup-start-time=03:00

# Создать базу данных
gcloud sql databases create your_app_production \
    --instance=your-app-db

# Создать пользователя
gcloud sql users create your_app_user \
    --instance=your-app-db \
    --password=your-secure-password
```

### 2. Настройка подключения

```bash
# Получить строку подключения
gcloud sql instances describe your-app-db \
    --format="value(connectionName)"

# Результат: your-project:region:your-app-db
```

---

## 🗂️ Настройка Cloud Storage

### 1. Создание buckets

```bash
# Bucket для статических файлов фронтенда
gsutil mb -l europe-west1 gs://your-app-frontend

# Bucket для медиа файлов
gsutil mb -l europe-west1 gs://your-app-media

# Настройка публичного доступа для фронтенда
gsutil iam ch allUsers:objectViewer gs://your-app-frontend

# Включить статический хостинг
gsutil web set -m index.html -e index.html gs://your-app-frontend
```

### 2. Настройка CORS для медиа

```bash
# Создать cors.json
cat > cors.json << EOF
[
  {
    "origin": ["https://app.your-domain.com"],
    "method": ["GET", "POST", "PUT", "DELETE"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
EOF

# Применить CORS
gsutil cors set cors.json gs://your-app-media
```

---

## 🔐 Управление секретами

### 1. Создание секретов

```bash
# Django secret key
echo -n "your-super-secure-django-secret-key" | \
    gcloud secrets create django-secret-key --data-file=-

# Database URL
echo -n "postgresql://your_app_user:your-secure-password@/your_app_production?host=/cloudsql/your-project:region:your-app-db" | \
    gcloud secrets create database-url --data-file=-

# Redis URL (если используете Redis на GCP)
echo -n "redis://your-redis-instance:6379/0" | \
    gcloud secrets create redis-url --data-file=-
```

### 2. Настройка доступа

```bash
# Получить email Cloud Run service account
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --format="table(bindings.role)" \
    --filter="bindings.members:*@$PROJECT_ID.iam.gserviceaccount.com"

# Дать доступ к секретам
gcloud secrets add-iam-policy-binding django-secret-key \
    --member="serviceAccount:your-cloudrun-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

---

## 🐳 Подготовка Docker образов

### 1. Backend Dockerfile

```dockerfile
# backend/Dockerfile.prod
FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установка uv
RUN pip install uv

# Копирование зависимостей
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Копирование кода
COPY . .

# Создание пользователя
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8080

# Cloud Run использует PORT переменную
ENV PORT=8080

CMD exec uv run gunicorn your_project.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120
```

### 2. Backend production settings

```python
# backend/your_project/settings/prod.py
import os
from .base import *

# Безопасность
DEBUG = False
ALLOWED_HOSTS = [
    'api.your-domain.com',
    '.run.app',  # Cloud Run домены
]

# Секреты из Secret Manager
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

# База данных Cloud SQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_app_production',
        'USER': 'your_app_user',
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': f'/cloudsql/{os.environ["CLOUD_SQL_CONNECTION_NAME"]}',
        'PORT': '5432',
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
    }
}

# Cloud Storage для статических и медиа файлов
DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
STATICFILES_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'

GS_BUCKET_NAME = 'your-app-media'
GS_STATIC_BUCKET_NAME = 'your-app-static'
GS_AUTO_CREATE_BUCKET = True
GS_DEFAULT_ACL = 'publicRead'

# CORS
CORS_ALLOWED_ORIGINS = [
    'https://app.your-domain.com',
    'https://your-domain.com',
]

# Логирование для Cloud Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

---

## 🚀 Деплой на Cloud Run

### 1. Сборка и пуш образа

```bash
# Сборка образа
cd backend
gcloud builds submit --tag gcr.io/$PROJECT_ID/your-app-backend .

# Или использовать Artifact Registry (рекомендуется)
gcloud artifacts repositories create your-app-repo \
    --repository-format=docker \
    --location=europe-west1

# Тегировать и пушить
docker tag gcr.io/$PROJECT_ID/your-app-backend \
    europe-west1-docker.pkg.dev/$PROJECT_ID/your-app-repo/backend

docker push europe-west1-docker.pkg.dev/$PROJECT_ID/your-app-repo/backend
```

### 2. Деплой на Cloud Run

```bash
gcloud run deploy your-app-backend \
    --image europe-west1-docker.pkg.dev/$PROJECT_ID/your-app-repo/backend \
    --platform managed \
    --region europe-west1 \
    --allow-unauthenticated \
    --add-cloudsql-instances $PROJECT_ID:europe-west1:your-app-db \
    --set-env-vars DJANGO_SETTINGS_MODULE=your_project.settings.prod \
    --set-env-vars CLOUD_SQL_CONNECTION_NAME=$PROJECT_ID:europe-west1:your-app-db \
    --set-secrets DJANGO_SECRET_KEY=django-secret-key:latest \
    --set-secrets DB_PASSWORD=database-password:latest \
    --memory 1Gi \
    --cpu 1000m \
    --timeout 300 \
    --concurrency 80
```

### 3. Применение миграций

```bash
# Получить URL сервиса
SERVICE_URL=$(gcloud run services describe your-app-backend \
    --region=europe-west1 \
    --format="value(status.url)")

# Запустить миграции через Cloud Run Jobs
gcloud run jobs create migrate-job \
    --image europe-west1-docker.pkg.dev/$PROJECT_ID/your-app-repo/backend \
    --region europe-west1 \
    --add-cloudsql-instances $PROJECT_ID:europe-west1:your-app-db \
    --set-env-vars DJANGO_SETTINGS_MODULE=your_project.settings.prod \
    --set-secrets DJANGO_SECRET_KEY=django-secret-key:latest \
    --command "uv" \
    --args "run,python,manage.py,migrate"

# Выполнить миграции
gcloud run jobs execute migrate-job --region=europe-west1
```

---

## 🌐 Настройка Load Balancer

### 1. Деплой фронтенда в Cloud Storage

```bash
cd frontend

# Создать production build
VITE_API_BASE=https://api.your-domain.com pnpm build

# Загрузить в Cloud Storage
gsutil -m rsync -r -d dist/ gs://your-app-frontend/

# Настроить кэширование
gsutil -m setmeta -h "Cache-Control:public, max-age=31536000" \
    gs://your-app-frontend/assets/**

gsutil -m setmeta -h "Cache-Control:public, max-age=3600" \
    gs://your-app-frontend/index.html
```

### 2. Создание Load Balancer

```bash
# Создать IP адрес
gcloud compute addresses create your-app-ip --global

# Получить IP
gcloud compute addresses describe your-app-ip --global

# Создать backend bucket для фронтенда
gcloud compute backend-buckets create frontend-backend \
    --gcs-bucket-name=your-app-frontend

# Создать backend service для API
gcloud compute backend-services create api-backend \
    --global \
    --load-balancing-scheme=EXTERNAL_MANAGED

# Добавить Cloud Run в backend service
gcloud compute backend-services add-backend api-backend \
    --global \
    --network-endpoint-group=your-app-backend-neg \
    --network-endpoint-group-region=europe-west1

# Создать URL map
gcloud compute url-maps create your-app-lb \
    --default-backend-bucket=frontend-backend

# Добавить маршрут для API
gcloud compute url-maps add-path-matcher your-app-lb \
    --path-matcher-name=api \
    --default-backend-service=api-backend \
    --backend-service-path-rules="/api/*=api-backend"

# Создать HTTPS proxy
gcloud compute target-https-proxies create your-app-https-proxy \
    --url-map=your-app-lb \
    --ssl-certificates=your-ssl-cert

# Создать forwarding rule
gcloud compute forwarding-rules create your-app-https-rule \
    --global \
    --target-https-proxy=your-app-https-proxy \
    --address=your-app-ip \
    --ports=443
```

### 3. Настройка SSL сертификата

```bash
# Создать управляемый SSL сертификат
gcloud compute ssl-certificates create your-ssl-cert \
    --domains=your-domain.com,app.your-domain.com,api.your-domain.com \
    --global
```

---

## 🔧 Настройка DNS

```bash
# Получить статический IP
STATIC_IP=$(gcloud compute addresses describe your-app-ip --global --format="value(address)")

echo "Настройте DNS записи:"
echo "A record: your-domain.com -> $STATIC_IP"
echo "A record: app.your-domain.com -> $STATIC_IP"  
echo "A record: api.your-domain.com -> $STATIC_IP"
```

---

## 🔄 CI/CD для GCP

### 1. Обновление GitHub Actions

```yaml
# .github/workflows/deploy-gcp.yml
name: 🚀 Deploy to GCP

on:
  push:
    branches: [main]

env:
  PROJECT_ID: your-project-id
  REGION: europe-west1
  SERVICE_NAME: your-app-backend

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: 📥 Checkout
        uses: actions/checkout@v4

      - name: 🔐 Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: 🛠️ Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: 🐳 Build and push Docker image
        run: |
          cd backend
          gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

      - name: 🚀 Deploy to Cloud Run
        run: |
          gcloud run deploy $SERVICE_NAME \
            --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
            --region $REGION \
            --platform managed \
            --allow-unauthenticated

      - name: 🌐 Deploy Frontend
        run: |
          cd frontend
          npm ci
          VITE_API_BASE=https://api.your-domain.com npm run build
          gsutil -m rsync -r -d dist/ gs://your-app-frontend/
```

---

## 📊 Мониторинг и логирование

### 1. Настройка Cloud Monitoring

```bash
# Создать notification channel
gcloud alpha monitoring channels create \
    --display-name="Email Alerts" \
    --type=email \
    --channel-labels=email_address=your-email@domain.com

# Создать uptime check
gcloud monitoring uptime-check-configs create \
    --display-name="Backend API Health" \
    --http-check-path="/api/health/" \
    --http-check-host="api.your-domain.com" \
    --timeout=10s \
    --period=60s
```

### 2. Настройка алертов

```bash
# Создать alert policy для ошибок
gcloud alpha monitoring policies create \
    --policy-from-file=monitoring-policy.yaml
```

---

## 💰 Оптимизация расходов

### 1. Настройка автоскейлинга

```bash
# Обновить сервис с автоскейлингом
gcloud run services update your-app-backend \
    --region=europe-west1 \
    --min-instances=0 \
    --max-instances=10 \
    --concurrency=80
```

### 2. Настройка Cloud SQL

```bash
# Включить автоматическое увеличение storage
gcloud sql instances patch your-app-db \
    --storage-auto-increase

# Настроить maintenance window
gcloud sql instances patch your-app-db \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=3
```

---

## 🔍 Troubleshooting

### Частые проблемы

1. **Cloud SQL connection issues**
   ```bash
   # Проверить статус Cloud SQL
   gcloud sql instances describe your-app-db
   
   # Проверить logs Cloud Run
   gcloud logs read --service=your-app-backend
   ```

2. **Frontend не загружается**
   ```bash
   # Проверить CORS настройки
   gsutil cors get gs://your-app-frontend
   
   # Проверить индексный файл
   gsutil ls -l gs://your-app-frontend/index.html
   ```

3. **SSL сертификат не активен**
   ```bash
   # Проверить статус сертификата
   gcloud compute ssl-certificates describe your-ssl-cert --global
   ```

---

## 📋 Checklist деплоя

### Подготовка
- [ ] Создан GCP проект
- [ ] Включены необходимые API
- [ ] Настроен Cloud SQL
- [ ] Созданы Cloud Storage buckets
- [ ] Настроены секреты в Secret Manager

### Деплой
- [ ] Backend образ собран и загружен
- [ ] Cloud Run сервис развернут
- [ ] Применены миграции базы данных
- [ ] Frontend загружен в Cloud Storage
- [ ] Настроен Load Balancer
- [ ] Создан SSL сертификат
- [ ] Настроены DNS записи

### Финализация  
- [ ] Настроен мониторинг
- [ ] Созданы алерты
- [ ] Настроен CI/CD pipeline
- [ ] Проведено smoke testing
- [ ] Создан план backup'ов

---

**🎉 Поздравляем! Ваше приложение развернуто на GCP!**

Доступ:
- 🌐 **Frontend**: https://app.your-domain.com
- 🔧 **API**: https://api.your-domain.com
- 📊 **Monitoring**: Google Cloud Console
