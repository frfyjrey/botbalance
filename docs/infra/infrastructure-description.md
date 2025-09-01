# 🚀 Infrastructure Description

## 🎯 Цель

Поднять прод-инфраструктуру для botbalance, не трогая бизнес-логику:

- **API** (Django+DRF) и **Celery worker** — в Cloud Run
- **База данных** — Cloud SQL (PostgreSQL)  
- **Очередь/кэш** — Upstash Redis (serverless)
- **Фронтенд** (Vite build) — Google Cloud Storage + HTTPS
- **Домены**: `api.botbalance.me` (Cloud Run), `app.botbalance.me` (GCS)
- **Секреты** — Google Secret Manager
- **CI/CD** — GitHub Actions (два пайплайна: CI уже есть; добавляем CD)

> **📝 Статус**: Репозиторий уже сконфигурирован и проходит CI. Задача — довести его до «кнопки деплой», настроить окружение в GCP и домены.

## 🏗️ Архитектура (высокоуровневая)

### Cloud Run
- **`botbalance-api`** — веб-сервис DRF (gunicorn/uvicorn)
- **`botbalance-worker`** — Celery worker (тот же образ, другой command)

### Хранилища данных
- **Cloud SQL (Postgres)** — основная БД. Подключение через Cloud Run → Cloud SQL (instance connection)
- **Upstash Redis** — брокер Celery и потенциальный кэш

### Управление секретами и артефактами  
- **Google Secret Manager** — секреты: `DJANGO_SECRET_KEY`, `DATABASE_URL`/DB creds, `REDIS_URL`, `ENCRYPTION_KEY`, `SENTRY_DSN` (если нужно)
- **Artifact Registry** — хранение образов backend
- **Cloud Storage bucket** — хостинг фронтенда (статический контент) + HTTPS (через LB или Cloudflare)

### Домены
- `api.botbalance.me` → Cloud Run (Managed SSL)
- `app.botbalance.me` → GCS (через HTTPS LB или через Cloudflare)

## 🔐 Безопасность (минимум, но правильно)

- **Секреты** — только в Secret Manager, доступ по IAM к Cloud Run сервисам
- **API-ключи бирж** (когда появятся) — шифровать в БД симметричным ключом (`ENCRYPTION_KEY`), который лежит в Secret Manager  
- **Cloud Run → Cloud SQL** — через instance connection (`--add-cloudsql-instances`), без публичного IP БД
- **CORS API**: разрешить только `https://app.botbalance.me`
- **CI/CD доступ к GCP** — service account JSON как GitHub Secret (быстрее) или OIDC (лучше, но сложнее). Для MVP — JSON

> **💡 Комментарий**: Подход с JSON service account ключом проще в настройке, но менее безопасен. OIDC Workload Identity Federation — best practice для продакшена.

## 🔁 Деплой (как это должно работать)

**Триггер**: Пушишь тег релиза (например, `v0.1.0`) или мержишь в `main`.

**GitHub Actions процесс**:

1. 🏗️ **Сборка backend образа** → публикация в Artifact Registry
2. 🗄️ **Прогон миграций** (однократный job)  
3. 🚀 **Деплой Cloud Run**: `botbalance-api` и `botbalance-worker`
4. 🌐 **Сборка фронта** → загрузка в GCS bucket (с кэш-заголовками)

**Проверка**:
- ✅ `https://api.botbalance.me/api/health` — OK
- ✅ `https://app.botbalance.me` — открывается, Dashboard делает запрос к `/api/health`

## ✅ Definition of Done

- [ ] Оба сервиса Cloud Run на месте, здоровы (health OK)
- [ ] Cloud SQL сконфигурирован и доступен из Cloud Run, без публичного входа
- [ ] Redis (Upstash) подключён, Celery worker активен
- [ ] `api.botbalance.me` и `app.botbalance.me` работают по HTTPS
- [ ] Секреты в Secret Manager, роли на сервис-аккаунте выданы минимально  
- [ ] GitHub Actions CD — деплой «одной кнопкой» (по тегу / merge)
- [ ] Документация описывает откат (rollback к предыдущему образу)

> **🎯 Итог**: После выполнения всех пунктов получается полностью автоматизированная инфраструктура с возможностью деплоя одной командой и безопасным управлением секретами.