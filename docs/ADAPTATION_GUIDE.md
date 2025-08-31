# 🚀 Руководство по адаптации бойлерплейта

Пошаговая инструкция по настройке этого бойлерплейта для вашего нового проекта.

---

## 📋 Содержание

1. [🎯 Быстрый старт](#-быстрый-старт)
2. [🏷️ Переименование проекта](#-переименование-проекта)
3. [🔧 Настройка Backend](#-настройка-backend)
4. [⚛️ Настройка Frontend](#-настройка-frontend)
5. [🐳 Конфигурация Docker](#-конфигурация-docker)
6. [🔄 Настройка CI/CD](#-настройка-cicd)
7. [🌐 Переменные окружения](#-переменные-окружения)
8. [📊 Мониторинг и логирование](#-мониторинг-и-логирование)
9. [🚀 Подготовка к продакшену](#-подготовка-к-продакшену)

---

## 🎯 Быстрый старт

### 1. Клонирование и переименование

```bash
# Клонируйте бойлерплейт
git clone <botbalance-repo-url> my-new-project
cd my-new-project

# Удалите git историю и создайте новый репозиторий
rm -rf .git
git init
git remote add origin <your-new-repo-url>
```

### 2. Первоначальная настройка

```bash
# Установите зависимости и запустите сервисы
make setup
make services

# Запустите разработку
make dev
```

Готово! Теперь переходите к детальной настройке ⬇️

---

## 🏷️ Переименование проекта

### Backend (Django)

#### 1. Название Django проекта

**Файлы для изменения:**

```bash
# Переименуйте папку app/ в ваше название
mv backend/app backend/your_project_name

# Обновите файлы:
backend/your_project_name/settings/base.py
backend/your_project_name/wsgi.py
backend/your_project_name/asgi.py
backend/your_project_name/celery.py
backend/manage.py
backend/pyproject.toml
```

**Изменения в коде:**

```python
# backend/your_project_name/settings/base.py
ROOT_URLCONF = 'your_project_name.urls'
WSGI_APPLICATION = 'your_project_name.wsgi.application'

# backend/your_project_name/celery.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project_name.settings.local')
app = Celery('your_project_name')

# backend/manage.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project_name.settings.local')
```

#### 2. Обновите pyproject.toml

```toml
[project]
name = "your-project-name"
description = "Your project description"

[project.urls]
Homepage = "https://github.com/yourusername/your-project"
Repository = "https://github.com/yourusername/your-project.git"
```

### Frontend (React)

#### 1. Обновите package.json

```json
{
  "name": "your-project-frontend",
  "description": "Your project frontend",
  "homepage": "https://your-domain.com"
}
```

#### 2. Обновите индекс файлы

```html
<!-- frontend/index.html -->
<title>Your Project Name</title>
<meta name="description" content="Your project description">
```

### Makefile

```makefile
# Makefile - обновите переменные в начале файла
PROJECT_NAME := your_project_name
BACKEND_APP := your_project_name
FRONTEND_APP := your-project-frontend
```

---

## 🔧 Настройка Backend

### 1. Создание Django приложений

```bash
cd backend
python manage.py startapp users      # Управление пользователями
python manage.py startapp products   # Ваша бизнес-логика
python manage.py startapp orders     # Пример дополнительного приложения
```

### 2. Настройка моделей

**Пример модели продукта:**

```python
# backend/products/models.py
from django.db import models
from django.contrib.auth.models import User

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
```

### 3. Настройка API эндпоинтов

**Создайте ViewSet для вашего API:**

```python
# backend/products/serializers.py
from rest_framework import serializers
from .models import Product

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ('created_by', 'created_at', 'updated_at')

# backend/products/views.py
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .models import Product
from .serializers import ProductSerializer

class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
```

### 4. Обновите настройки

```python
# backend/your_project_name/settings/base.py
INSTALLED_APPS = [
    # ... существующие
    'products',
    'orders',
    'users',
]

# backend/your_project_name/urls.py
from products.views import ProductViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'products', ProductViewSet)

urlpatterns = [
    # ... существующие
    path('api/', include(router.urls)),
]
```

### 5. Создание и применение миграций

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## ⚛️ Настройка Frontend

### 1. Структура фичей (FSD-lite)

**Создайте новые фичи:**

```bash
frontend/src/
├── entities/
│   ├── product/          # Новая сущность
│   │   ├── api.ts
│   │   ├── model.ts
│   │   └── index.ts
│   └── order/           # Еще одна сущность
├── features/
│   ├── product-list/    # Список продуктов
│   ├── product-form/    # Форма создания/редактирования
│   └── order-management/
└── pages/
    ├── products/        # Страница продуктов
    └── orders/         # Страница заказов
```

### 2. Настройка API клиента

```typescript
// frontend/src/entities/product/api.ts
import { apiClient } from '@shared/lib/api';

export interface Product {
  id: number;
  name: string;
  description: string;
  price: string;
  created_at: string;
  updated_at: string;
}

export const productAPI = {
  getAll: (): Promise<Product[]> =>
    apiClient.get('/products/'),
    
  getById: (id: number): Promise<Product> =>
    apiClient.get(`/products/${id}/`),
    
  create: (data: Partial<Product>): Promise<Product> =>
    apiClient.post('/products/', data),
    
  update: (id: number, data: Partial<Product>): Promise<Product> =>
    apiClient.patch(`/products/${id}/`, data),
    
  delete: (id: number): Promise<void> =>
    apiClient.delete(`/products/${id}/`),
};
```

### 3. Настройка роутинга

```typescript
// frontend/src/app/routes/index.tsx
import { ProductListPage } from '@pages/products';
import { ProductDetailPage } from '@pages/products/detail';

export const routes = createBrowserRouter([
  // ... существующие маршруты
  {
    path: '/products',
    element: <ProtectedRoute><ProductListPage /></ProtectedRoute>,
  },
  {
    path: '/products/:id',
    element: <ProtectedRoute><ProductDetailPage /></ProtectedRoute>,
  },
]);
```

### 4. Настройка интернационализации

```json
// frontend/src/locales/ru/products.json
{
  "title": "Продукты",
  "create": "Создать продукт",
  "edit": "Редактировать",
  "delete": "Удалить",
  "name": "Название",
  "description": "Описание",
  "price": "Цена"
}

// frontend/src/locales/en/products.json
{
  "title": "Products",
  "create": "Create Product",
  "edit": "Edit",
  "delete": "Delete",
  "name": "Name",
  "description": "Description",
  "price": "Price"
}
```

---

## 🐳 Конфигурация Docker

### 1. Обновите docker-compose.yml

```yaml
# Добавьте новые сервисы если нужно
services:
  # ... существующие сервисы
  
  # Elasticsearch для поиска (пример)
  elasticsearch:
    image: elasticsearch:8.11.0
    container_name: your_project_elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

volumes:
  # ... существующие
  elasticsearch_data:
    driver: local
```

### 2. Создайте production Dockerfile

```dockerfile
# backend/Dockerfile.prod
FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установка Python зависимостей
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Копирование кода
COPY . .

# Настройка пользователя
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["uv", "run", "gunicorn", "your_project.wsgi:application", "--bind", "0.0.0.0:8000"]
```

---

## 🔄 Настройка CI/CD

### 1. Обновите GitHub Actions

**Измените переменные в `.github/workflows/ci.yml`:**

```yaml
env:
  PROJECT_NAME: "your-project"
  BACKEND_SETTINGS: "your_project.settings.local"
  
jobs:
  backend-tests:
    env:
      DJANGO_SETTINGS_MODULE: your_project.settings.local
```

### 2. Настройте Dependabot

**Обновите `.github/dependabot.yml`:**

```yaml
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    reviewers:
      - "your-github-username"    # ИЗМЕНИТЕ
    assignees:
      - "your-github-username"    # ИЗМЕНИТЕ
```

### 3. Добавьте deployment workflow

```yaml
# .github/workflows/deploy.yml
name: 🚀 Deploy to Production

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  deploy:
    name: Deploy to GCP
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: 📥 Checkout code
        uses: actions/checkout@v4
        
      # Добавьте ваши шаги деплоя
      - name: 🚀 Deploy to Cloud Run
        run: |
          # Ваши команды деплоя
          echo "Deploy to production"
```

---

## 🌐 Переменные окружения

### 1. Создайте production настройки

```bash
# Скопируйте примеры
cp env.example .env
cp frontend/env.example frontend/.env

# Настройте production переменные
cp .env .env.production
```

### 2. Production переменные

```bash
# .env.production
DJANGO_SECRET_KEY=your-super-secure-secret-key
DATABASE_URL=postgresql://user:pass@your-db-host:5432/your_db
REDIS_URL=redis://your-redis-host:6379/0

# CORS и безопасность
ALLOWED_HOSTS=your-domain.com,api.your-domain.com
CORS_ALLOWED_ORIGINS=https://your-domain.com

# Email настройки
EMAIL_HOST=smtp.your-provider.com
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password

# Внешние сервисы
SENTRY_DSN=your-sentry-dsn
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
```

### 3. Frontend переменные

```bash
# frontend/.env.production
VITE_API_BASE=https://api.your-domain.com
VITE_ENVIRONMENT=production
VITE_SENTRY_DSN=your-frontend-sentry-dsn
```

---

## 📊 Мониторинг и логирование

### 1. Подключите Sentry

```python
# backend/your_project/settings/prod.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=env('SENTRY_DSN'),
    integrations=[
        DjangoIntegration(auto_enabling_integrations=False),
        CeleryIntegration(),
    ],
    traces_sample_rate=0.1,
    send_default_pii=True
)
```

### 2. Настройте логирование

```python
# backend/your_project/settings/base.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'botbalance.log',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        'your_project': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

---

## 🚀 Подготовка к продакшену

### 1. Безопасность

```python
# backend/your_project/settings/prod.py
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
```

### 2. Статические файлы

```python
# backend/your_project/settings/prod.py
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Для GCS или S3
DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
GS_BUCKET_NAME = 'your-bucket-name'
```

### 3. База данных

```python
# backend/your_project/settings/prod.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'options': '-c default_transaction_isolation=serializable'
        },
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
    }
}
```

### 4. Кэширование

```python
# backend/your_project/settings/prod.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL'),
        'KEY_PREFIX': 'your_project',
        'TIMEOUT': 300,
    }
}
```

---

## 🎯 Чек-лист адаптации

### Обязательно

- [ ] Переименовать проект во всех конфигурациях
- [ ] Обновить переменные окружения
- [ ] Настроить домены и CORS
- [ ] Создать production базу данных
- [ ] Настроить CI/CD pipeline
- [ ] Добавить мониторинг (Sentry)
- [ ] Настроить автоматические бэкапы

### Рекомендуемо

- [ ] Добавить rate limiting
- [ ] Настроить CDN для статики
- [ ] Подключить аналитику
- [ ] Добавить health checks
- [ ] Настроить алерты
- [ ] Документировать API (OpenAPI)

### При необходимости

- [ ] Мультитенантность
- [ ] Микросервисная архитектура
- [ ] GraphQL API
- [ ] Real-time функциональность (WebSockets)
- [ ] Мобильное приложение (API адаптация)

---

## 🆘 Получение помощи

### Документация

- [Django Documentation](https://docs.djangoproject.com/)
- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)

### Сообщество

- [Django Discord](https://discord.gg/xcRH6mN4fa)
- [Reactiflux Discord](https://discord.gg/reactiflux)

### Инструменты для деплоя

- [Google Cloud Platform](https://cloud.google.com/)
- [AWS](https://aws.amazon.com/)
- [DigitalOcean](https://digitalocean.com/)
- [Railway](https://railway.app/)

---

**Удачи с вашим новым проектом! 🚀**
