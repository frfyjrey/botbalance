# 🚀 GitHub Actions Deployment Setup

## 📋 **Обзор**

Этот документ описывает настройку автоматического деплоя BotBalance через GitHub Actions.

## 🔐 **Настройка GitHub Secrets**

### **Шаг 1: Создание Service Account в GCP**

```bash
# 1. Создаем сервисный аккаунт для GitHub Actions
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deploy" \
  --description="Service account for GitHub Actions deployments"

# 2. Назначаем необходимые роли
gcloud projects add-iam-policy-binding botbalance \
  --member="serviceAccount:github-actions@botbalance.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding botbalance \
  --member="serviceAccount:github-actions@botbalance.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding botbalance \
  --member="serviceAccount:github-actions@botbalance.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.admin"

gcloud projects add-iam-policy-binding botbalance \
  --member="serviceAccount:github-actions@botbalance.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding botbalance \
  --member="serviceAccount:github-actions@botbalance.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 3. Создаем ключ
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions@botbalance.iam.gserviceaccount.com
```

### **Шаг 2: Добавление Secrets в GitHub**

Перейди в GitHub репозиторий → Settings → Secrets and variables → Actions

**Repository secrets:**

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `GCP_SA_KEY` | Содержимое файла `github-actions-key.json` | Ключ сервисного аккаунта GCP |

**Environment secrets (для production):**

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `GCP_SA_KEY` | Содержимое файла `github-actions-key.json` | Дублируем для environment |

### **Шаг 3: Создание Environments**

1. Перейди в **Settings → Environments**
2. Создай environment `production`
3. Настрой **Environment protection rules:**
   - ✅ Required reviewers (себя)
   - ✅ Wait timer: 0 minutes
   - ✅ Deployment branches: Selected branches → `main`

## 🚀 **Деплой процесс**

### **Автоматический деплой (рекомендуется)**

```bash
# 1. Создай и запуши тег
git tag v1.0.0
git push origin v1.0.0

# 2. Workflows запустятся автоматически
# Backend: .github/workflows/deploy-backend.yml
# Frontend: .github/workflows/deploy-frontend.yml
```

### **Ручной деплой**

1. Перейди в **Actions** tab
2. Выбери workflow `Deploy Backend` или `Deploy Frontend`
3. Нажми **Run workflow**
4. Выбери параметры и нажми **Run workflow**

## 🔄 **Rollback процесс**

### **Backend Rollback**

```bash
# Откат к предыдущей ревизии
gcloud run services update-traffic botbalance-api \
  --to-revisions=LATEST=100 \
  --region=asia-southeast1

gcloud run services update-traffic botbalance-worker \
  --to-revisions=LATEST=100 \
  --region=asia-southeast1
```

### **Frontend Rollback**

```bash
# Передеплой предыдущего тега
git checkout v1.0.0
# Запушь тег заново или используй ручной деплой
```

## 🔍 **Мониторинг**

### **Проверка деплоя**

```bash
# Backend health check
curl https://api.botbalance.me/api/health/

# Frontend check
curl https://app.botbalance.me

# Celery worker logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=botbalance-worker" --limit=10
```

### **Полезные команды**

```bash
# Список ревизий Cloud Run
gcloud run revisions list --service=botbalance-api --region=asia-southeast1

# Логи деплоя
gcloud logging read "resource.type=cloud_run_revision" --limit=20

# Статус сервисов
gcloud run services list --region=asia-southeast1
```

## 🛠️ **Troubleshooting**

### **Частые ошибки**

| Ошибка | Решение |
|--------|---------|
| `Permission denied` | Проверь роли сервисного аккаунта |
| `Image not found` | Проверь что образ собрался и запушился |
| `Migration failed` | Проверь доступ к Cloud SQL и секреты |
| `Health check failed` | Проверь логи сервиса и настройки |

### **Debugging**

```bash
# Проверить deployment
gcloud run services describe botbalance-api --region=asia-southeast1

# Проверить логи
gcloud logs tail projects/botbalance/logs/run.googleapis.com%2Frequests

# Проверить секреты
gcloud secrets versions access latest --secret="DJANGO_SECRET_KEY"
```

## 📝 **Чек-лист после настройки**

- [ ] ✅ Сервисный аккаунт создан с правильными ролями
- [ ] ✅ GitHub Secrets добавлены (GCP_SA_KEY)
- [ ] ✅ Environment `production` создан
- [ ] ✅ Тестовый деплой по тегу прошел успешно
- [ ] ✅ Backend health check возвращает 200
- [ ] ✅ Frontend загружается и работает
- [ ] ✅ Celery worker обрабатывает задачи
- [ ] ✅ Rollback процесс протестирован

## 🔮 **Будущие улучшения**

- **Blue-Green Deployment** - деплой без даунтайма
- **Automated Testing** - интеграционные тесты перед продом
- **Slack Notifications** - уведомления о деплоях
- **Metrics Dashboard** - мониторинг производительности
- **Staging Environment** - тестовая среда перед продом
