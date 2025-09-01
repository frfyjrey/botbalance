# 📋 Infrastructure Tasks

> Детальная пошаговка (one-by-one). Копируй и выполняй по порядку.

## 📋 Предусловия

- ✅ У тебя есть доступ Owner/Editor к GCP проекту (назовём `<GCP_PROJECT>`)
- ✅ Домены управляются в Cloudflare (или другом DNS)
- ✅ `gcloud` CLI установлен и настроен

---

## 1️⃣ Включить нужные API в GCP

**Необходимые API:**
- Cloud Run
- Cloud SQL Admin  
- Secret Manager
- Artifact Registry
- Cloud Build (опционально)
- Compute Engine (для LB фронта, если пойдёшь через GCLB)

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com
```

## 2️⃣ Artifact Registry (реестр образов)

Создай репозиторий для бэкенда:

```bash
gcloud artifacts repositories create botbalance-backend \
  --repository-format=docker \
  --location=asia-southeast1 \
  --description="Backend images for botbalance"
```

> **📝 Запомни полный путь**: `asia-southeast1-docker.pkg.dev/<GCP_PROJECT>/botbalance-backend`

---

## 3️⃣ Service Account для деплоя из GitHub

### Создать сервис-аккаунт:

```bash
gcloud iam service-accounts create gh-deployer \
  --display-name="GitHub Actions Deployer"
```

### Выдать роли (минимально необходимые):

```bash
# Cloud Run управление
gcloud projects add-iam-policy-binding <GCP_PROJECT> \
  --member="serviceAccount:gh-deployer@<GCP_PROJECT>.iam.gserviceaccount.com" \
  --role="roles/run.admin"

# Artifact Registry запись
gcloud projects add-iam-policy-binding <GCP_PROJECT> \
  --member="serviceAccount:gh-deployer@<GCP_PROJECT>.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# Secret Manager чтение
gcloud projects add-iam-policy-binding <GCP_PROJECT> \
  --member="serviceAccount:gh-deployer@<GCP_PROJECT>.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Cloud SQL подключение  
gcloud projects add-iam-policy-binding <GCP_PROJECT> \
  --member="serviceAccount:gh-deployer@<GCP_PROJECT>.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

### Создать JSON-ключ и сохранить его как GitHub Secret:

```bash
gcloud iam service-accounts keys create gh-deployer.json \
  --iam-account=gh-deployer@<GCP_PROJECT>.iam.gserviceaccount.com

# Открой gh-deployer.json и скопируй в GitHub Secrets как GCP_SA_KEY
```

### Также добавь в GitHub Secrets:
- `GCP_PROJECT` 
- `GCP_REGION` (например, `asia-southeast1`)
- `AR_REPO` (полный путь Artifact Registry)
- `FRONTEND_BUCKET` (позже)

> **⚠️ Безопасность**: Более безопасно настроить OIDC Workload Identity Federation и не хранить JSON-ключ. Для MVP можно оставить JSON.

## 4️⃣ Cloud SQL (PostgreSQL)

### Создать инстанс:

```bash
gcloud sql instances create botbalance-db \
  --database-version=POSTGRES_15 \
  --cpu=2 --memory=7680MB \
  --region=asia-southeast1
```

> **💰 Комментарий**: Для MVP можно начать с меньших ресурсов (1 CPU, 3.75GB RAM) и масштабировать по необходимости.

### Создать базу и пользователя:

```bash
gcloud sql databases create appdb --instance=botbalance-db
gcloud sql users create appuser --instance=botbalance-db --password="<STRONG_PASSWORD>"
```

> **📝 Запомни instance connection name**: `<GCP_PROJECT>:asia-southeast1:botbalance-db`

## 5️⃣ Upstash Redis

1. Создай Redis database в [Upstash Console](https://console.upstash.com/) (Free/Serverless tier)
2. Скопируй `REDIS_URL` (формат `rediss://...`)

> **💡 Почему Upstash**: Serverless Redis идеально подходит для Celery — платишь только за использование, автомасштабирование.

## 6️⃣ Secret Manager — загрузить секреты

### Сгенерируй ключи:

```bash
# Генерация ENCRYPTION_KEY (Fernet)
python - <<'PY'
from cryptography.fernet import Fernet
print("FERNET:", Fernet.generate_key().decode())
PY

# Генерация Django SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Создай секреты:

```bash
# Django секретный ключ
echo -n "<your_django_secret>" | gcloud secrets create DJANGO_SECRET_KEY --data-file=-

# Database URL
echo -n "postgresql://appuser:<STRONG_PASSWORD>@127.0.0.1:5432/appdb" | gcloud secrets create DATABASE_URL --data-file=-

# Redis URL от Upstash
echo -n "<REDIS_URL_FROM_UPSTASH>" | gcloud secrets create REDIS_URL --data-file=-

# Ключ шифрования для API ключей бирж
echo -n "<FERNET_KEY>" | gcloud secrets create ENCRYPTION_KEY --data-file=-

# CORS настройки (опционально)
echo -n "https://app.botbalance.me" | gcloud secrets create CORS_ALLOWED_ORIGINS --data-file=-
```

---

## 7️⃣ Cloud Run: деплой backend API

### Собрать и запушить образ

> Можно из локалки или через Actions; тут — локально для первого запуска

```bash
# Сборка образа
docker build -t asia-southeast1-docker.pkg.dev/<GCP_PROJECT>/botbalance-backend/api:latest ./backend

# Push в Artifact Registry  
docker push asia-southeast1-docker.pkg.dev/<GCP_PROJECT>/botbalance-backend/api:latest
```

### Деплой API сервиса:

```bash
gcloud run deploy botbalance-api \
  --image=asia-southeast1-docker.pkg.dev/<GCP_PROJECT>/botbalance-backend/api:latest \
  --region=asia-southeast1 \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances=<GCP_PROJECT>:asia-southeast1:botbalance-db \
  --set-secrets=DJANGO_SECRET_KEY=DJANGO_SECRET_KEY:latest,REDIS_URL=REDIS_URL:latest,ENCRYPTION_KEY=ENCRYPTION_KEY:latest \
  --set-env-vars=DATABASE_HOST=/cloudsql/<GCP_PROJECT>:asia-southeast1:botbalance-db,DJANGO_SETTINGS_MODULE=botbalance.settings.prod,ALLOWED_HOSTS=api.botbalance.me \
  --memory=512Mi --cpu=1 --concurrency=40 --min-instances=1
```

> **🔌 Подключение к Cloud SQL**: В `prod.py` читай `DATABASE_URL` или собирай строку из `DATABASE_HOST=/cloudsql/...`. Самый простой путь — хранить `DATABASE_URL` как `postgresql://appuser:pass@127.0.0.1:5432/appdb` и задать `--add-cloudsql-instances` + использовать сокет `/cloudsql/...`

## 8️⃣ Cloud Run: деплой Celery worker

> Тот же образ, другая команда

```bash
gcloud run deploy botbalance-worker \
  --image=asia-southeast1-docker.pkg.dev/<GCP_PROJECT>/botbalance-backend/api:latest \
  --region=asia-southeast1 \
  --platform=managed \
  --no-allow-unauthenticated \
  --add-cloudsql-instances=<GCP_PROJECT>:asia-southeast1:botbalance-db \
  --set-secrets=DJANGO_SECRET_KEY=DJANGO_SECRET_KEY:latest,REDIS_URL=REDIS_URL:latest,ENCRYPTION_KEY=ENCRYPTION_KEY:latest \
  --set-env-vars=DJANGO_SETTINGS_MODULE=botbalance.settings.prod \
  --memory=512Mi --cpu=1 --concurrency=8 --min-instances=0 \
  --command="celery" --args="-A,botbalance,worker,-l,info"
```

> **🔧 Настройка**: `--min-instances=0` означает что worker будет "спать" без нагрузки и автоматически запускаться при поступлении задач в Celery.

---

## 9️⃣ Домены: api.botbalance.me

### Настройка в GCP:
1. Cloud Run → **Domain mappings** → привязать `api.botbalance.me`
2. Пройти верификацию домена, дождаться managed SSL

### Настройка в Cloudflare:
1. Создать **CNAME/A запись** по инструкции (из Domain mappings)  
2. Проверить `https://api.botbalance.me/api/health`

> **⏰ Время ожидания**: SSL сертификат может выдаваться до 15 минут.

## 🔟 Frontend: GCS bucket + HTTPS

### Создать bucket для фронта:

```bash
gsutil mb -l asia-southeast1 gs://app.botbalance.me
gsutil iam ch allUsers:objectViewer gs://app.botbalance.me
```

> Публичное чтение объектов

### Заливка билда:

```bash
cd frontend
pnpm install --frozen-lockfile  
pnpm build
gsutil -m rsync -r dist gs://app.botbalance.me
```

### HTTPS к бакету — два варианта

#### **Вариант A (проще): Cloudflare**

1. В Cloudflare укажи CNAME: `app.botbalance.me` → `c.storage.googleapis.com`
2. Включи HTTPS/SSL **Flexible** или **Full**
3. Проверь открытие сайта

#### **Вариант B (чище GCP): HTTPS Load Balancer + Backend bucket**

1. Создай Backend Bucket на `app.botbalance.me`
2. Подними HTTPS LB с Managed cert для домена и привязкой к bucket  
3. В Cloudflare укажи A/AAAA на внешний IP LB

> **💡 Рекомендация**: Для MVP используй **Вариант A** — проще в настройке и дешевле.

## 1️⃣1️⃣ CORS и проверка end-to-end

### Настройка CORS:
В Secret Manager (или env) на API: `CORS_ALLOWED_ORIGINS=https://app.botbalance.me`

### Проверка в браузере:

1. ✅ Открыть `https://app.botbalance.me`
2. ✅ Залогиниться (если включено)  
3. ✅ Dashboard должен сходить на `https://api.botbalance.me/api/health` и отобразить OK

> **🐛 Дебаг**: Если есть CORS ошибки, проверь что в Django settings правильно настроены `CORS_ALLOWED_ORIGINS` и `ALLOWED_HOSTS`.

---

## 1️⃣2️⃣ GitHub Actions — CD пайплайн

Создай `.github/workflows/deploy.yml`, который **по тегу**:

1. 🔐 **Логинится в GCP** с `GCP_SA_KEY`
2. 🏗️ **Собирает и пушит образ** в Artifact Registry  
3. 🗄️ **Прогоняет миграции** (отдельный шаг, `python manage.py migrate` через `gcloud run jobs` или как один-разовый Cloud Run job)
4. 🚀 **Деплоит** `botbalance-api` и `botbalance-worker`
5. 🌐 **Собирает фронт** и заливает в GCS bucket

> **📝 Последовательность**: CI у тебя уже есть. В CD обязательно добавь **«миграции → деплой → фронт»**.

## 1️⃣3️⃣ Health/rollback/алерты

### Health мониторинг:
- **Cloud Run** показывает состояние сервисов
- **Дополни** `/api/health` проверкой БД и Redis
- **Добавь** endpoint `/api/health/detailed` с проверкой всех компонентов

### Rollback:
```bash
# Откат на предыдущую версию
gcloud run services update-traffic botbalance-api --to-revisions=PREV=100 --region=asia-southeast1
gcloud run services update-traffic botbalance-worker --to-revisions=PREV=100 --region=asia-southeast1
```

### Алерты (опционально):
- **Sentry** (по желанию): добавь DSN в Secret Manager и подключи в Django
- **Cloud Monitoring** для мониторинга метрик Cloud Run

---

## 1️⃣4️⃣ Финальный чек-лист

- [ ] ✅ `api.botbalance.me/api/health` — OK по HTTPS
- [ ] ✅ `app.botbalance.me` отдаёт фронт, CORS работает  
- [ ] 🔐 Секреты в Secret Manager, роли выданы минимально
- [ ] 🚀 GitHub Actions CD деплоит по тегу и виден в логах
- [ ] 📖 Документация обновлена: как деплоить/роллбекать
- [ ] 🗄️ Database миграции работают автоматически
- [ ] 🔄 Celery worker обрабатывает задачи
- [ ] 🌐 Frontend обновляется при деплое

---

## 🎯 Результат

После выполнения всех шагов у тебя будет:
- **Полностью автоматизированный деплой** по тегу через GitHub Actions  
- **Безопасное управление секретами** через Secret Manager
- **Масштабируемая инфраструктура** на serverless компонентах
- **Простой rollback** одной командой

> **💡 Готовые файлы**: При необходимости могу предоставить готовый скелет `deploy.yml` и минимальные фрагменты `settings.prod.py` для Cloud SQL/Secrets — вставишь и запускаешь.