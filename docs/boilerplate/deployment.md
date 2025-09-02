# 🚀 Production деплой в GCP

> **Цель:** Задеплоить проект в GCP с автоматическим CI/CD через GitHub Actions.

## 📋 **Что получишь:**
- ✅ Django API на `https://api.your-domain.com`
- ✅ React SPA на `https://app.your-domain.com`
- ✅ PostgreSQL Cloud SQL + Upstash Redis
- ✅ SSL сертификаты + Load Balancer
- ✅ Автодеплой по git тегам
- ✅ Celery worker для задач

## ⏱️ **Время:** ~45-60 минут первый раз

---

## 🔧 **Шаг 1: GCP инфраструктура**

### 1.1. Создай GCP проект:
```bash
# В Google Cloud Console:
PROJECT_ID="your-project-prod"
REGION="asia-southeast1"  # Или ближайший к тебе
```

### 1.2. Активируй APIs:
```bash
gcloud services enable run.googleapis.com \
  cloudsql.googleapis.com \
  compute.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

### 1.3. Создай Artifact Registry:
```bash
gcloud artifacts repositories create your-project-backend \
  --repository-format=docker \
  --location=$REGION
```

### 1.4. Создай Cloud SQL (PostgreSQL):
```bash
gcloud sql instances create your-project-pg \
  --database-version=POSTGRES_15 \
  --cpu=1 --memory=3840MiB \
  --storage-type=SSD --storage-size=20GB \
  --region=$REGION
  
# Создай базу и пользователя
gcloud sql databases create your_project_db --instance=your-project-pg
gcloud sql users create your_project_user --instance=your-project-pg --password='STRONG_PASSWORD'
```

---

## 🗄️ **Шаг 2: Внешние сервисы**

### 2.1. Upstash Redis:
1. Зарегистрируйся на [Upstash](https://upstash.com)
2. Создай Redis базу в регионе близком к твоему GCP
3. Скопируй `REDIS_URL` (начинается с `rediss://`)

### 2.2. Домен (Cloudflare):
1. Купи домен (например на Cloudflare) 
2. Пока НЕ настраивай DNS записи - сделаем позже
3. Домен должен быть активен и доступен для управления

---

## 🔐 **Шаг 3: Секреты в GCP**

### 3.1. Создай секреты:
```bash
# Django secret key (сгенерируй)
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
gcloud secrets create DJANGO_SECRET_KEY --data-file=-  # Вставь ключ

# Fernet encryption key  
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
gcloud secrets create ENCRYPTION_KEY --data-file=-  # Вставь ключ

# Database
echo "DB_HOST" | gcloud secrets create DB_HOST --data-file=-
echo "/cloudsql/$PROJECT_ID:$REGION:your-project-pg" | gcloud secrets create DB_HOST --data-file=-
echo "your_project_db" | gcloud secrets create DB_NAME --data-file=-  
echo "your_project_user" | gcloud secrets create DB_USER --data-file=-
echo "STRONG_PASSWORD" | gcloud secrets create DB_PASSWORD --data-file=-

# Redis
echo "rediss://your-upstash-url?ssl_cert_reqs=required" | gcloud secrets create REDIS_URL --data-file=-

# CORS (для фронта)
echo "https://app.your-domain.com" | gcloud secrets create CORS_ALLOWED_ORIGINS --data-file=-
```

### 3.2. Создай сервисный аккаунт для runtime:
```bash
gcloud iam service-accounts create your-project-runtime \
  --display-name="Your Project Runtime"

# Назначь роли
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:your-project-runtime@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:your-project-runtime@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 🎯 **Шаг 4: GitHub Actions**

### 4.1. Создай сервисный аккаунт для CI/CD:
```bash
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deploy"

# ⚠️ КРИТИЧНО - ВСЕ роли нужны:
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# ⚠️ БЕЗ ЭТОГО МИГРАЦИИ НЕ РАБОТАЮТ:
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

### 4.2. Создай ключ и добавь в GitHub:
```bash
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions@$PROJECT_ID.iam.gserviceaccount.com

# Скопируй содержимое файла:
cat github-actions-key.json

# В GitHub репо → Settings → Secrets and variables → Actions
# Создай секрет: GCP_SA_KEY = содержимое JSON файла

# Удали файл:
rm github-actions-key.json
```

### 4.3. Создай GitHub Environment:
1. GitHub → Settings → Environments
2. Создай environment: `production`  
3. Environment protection rules → Add yourself as reviewer

---

## 🌐 **Шаг 5: Load Balancer + SSL**

### 5.1. Создай Cloud Storage bucket для фронта:
```bash
gsutil mb gs://app.your-domain.com
gsutil web set -m index.html gs://app.your-domain.com
gsutil iam ch allUsers:objectViewer gs://app.your-domain.com
```

### 5.2. Создай backend bucket для Load Balancer:
```bash
gcloud compute backend-buckets create your-project-frontend-backend \
  --gcs-bucket-name=app.your-domain.com \
  --global
```

### 5.3. Создай SSL сертификат:
```bash
gcloud compute ssl-certificates create your-project-ssl-cert \
  --domains=app.your-domain.com \
  --global
```

### 5.4. Создай URL map:
```bash
# Используй ops/urlmap-config.yaml (уже настроен для SPA routing)
gcloud compute url-maps import your-project-url-map \
  --source=ops/urlmap-config.yaml \
  --global
```

### 5.5. Создай статический IP:
```bash
gcloud compute addresses create your-project-ip --global
```

### 5.6. Создай HTTPS proxy и forwarding rule:
```bash
gcloud compute target-https-proxies create your-project-https-proxy \
  --ssl-certificates=your-project-ssl-cert \
  --url-map=your-project-url-map \
  --global

# Получи статический IP  
STATIC_IP=$(gcloud compute addresses describe your-project-ip --global --format="value(address)")

gcloud compute forwarding-rules create your-project-https-rule \
  --address=$STATIC_IP \
  --global \
  --target-https-proxy=your-project-https-proxy \
  --ports=443

# HTTP redirect на HTTPS:
gcloud compute url-maps import your-project-http-redirect \
  --source=ops/http-redirect-config.yaml \
  --global

gcloud compute target-http-proxies create your-project-http-proxy \
  --url-map=your-project-http-redirect \
  --global

gcloud compute forwarding-rules create your-project-http-rule \
  --address=$STATIC_IP \
  --global \
  --target-http-proxy=your-project-http-proxy \
  --ports=80
```

---

## 📍 **Шаг 6: DNS настройка**

### 6.1. Настрой DNS записи:
```bash
# В Cloudflare (или другом DNS):
# A record: app.your-domain.com → STATIC_IP (34.x.x.x)
# DNS only (не Proxied!) - важно для SSL

echo "Static IP: $STATIC_IP"
```

### 6.2. Дождись активации SSL:
```bash
# Проверяй статус (обычно 5-15 минут):
gcloud compute ssl-certificates list --global

# Должно быть: MANAGED_STATUS = ACTIVE
```

---

## 🚀 **Шаг 7: Первый деплой**

### 7.1. Запусти автодеплой:
```bash
# В локальной папке проекта:
git add .
git commit -m "feat: initial production setup"
git push origin main

# Создай релизный тег:
git tag v1.0.0
git push origin v1.0.0

# 🎬 Наблюдай магию в GitHub Actions!
```

### 7.2. Следи за прогрессом:
- GitHub → Actions → Workflows
- Должно запуститься 2 workflow:
  - `🚀 Deploy Backend`
  - `🎨 Deploy Frontend` 

### 7.3. Проверь результат (~5 минут):
- ✅ **API:** https://api.your-domain.com/api/health/
- ✅ **Frontend:** https://app.your-domain.com
- ✅ **Admin:** https://api.your-domain.com/nukoadmin/

---

## ✅ **Шаг 8: Создай суперпользователя**

### 8.1. Создай Django admin:
```bash
# Через Cloud Run Job (уже настроена):
gcloud run jobs execute your-project-create-superuser --region=$REGION
```

### 8.2. Проверь логин:
- Открой: https://api.your-domain.com/nukoadmin/
- Логин: admin / AdminPass123! (или твой пароль)

---

## 🐛 **Типичные проблемы и решения:**

### SSL Certificate в статусе FAILED_NOT_VISIBLE:
```bash
# DNS еще не обновился, подожди 15-30 минут
# Проверь что DNS запись правильная:
dig app.your-domain.com
```

### Cloud Run Job создается но не выполняется:
```bash
# Проверь IAM роли GitHub Actions сервисного аккаунта
# Особенно roles/iam.serviceAccountUser - БЕЗ НЕГО НЕ РАБОТАЕТ
```

### Frontend 404 на /dashboard и других роутах:
```bash
# URL map должен включать redirect правило для SPA
# Проверь ops/urlmap-config.yaml - там уже настроено
```

### "Connection reset by peer":
```bash  
# У HTTP и HTTPS forwarding rules разные IP адреса
# Нужен статический IP для обоих
```

### Celery worker падает сразу:
```bash
# Проверь REDIS_URL - должен содержать ?ssl_cert_reqs=required
# Не ?ssl_cert_reqs=CERT_NONE
```

---

## 🎉 **Готово!**

Теперь у тебя полностью автоматизированный production deployment:
- **Создаешь git tag** → автоматически деплоится все
- **SSL, Load Balancer, CDN** настроены  
- **Database миграции** выполняются автоматически
- **Health checks** проверяют что все работает

**Для rollback:** Создай тег предыдущей версии или используй `gcloud run services update-traffic`

**Следующий шаг:** [Справочники](reference.md)
