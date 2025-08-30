# ⚡ Quick Setup Guide

Быстрая настройка бойлерплейта для нового проекта за 15 минут.

---

## 🚀 1. Клонирование (2 мин)

```bash
# Клонировать бойлерплейт
git clone <boilerplate-repo> my-new-project
cd my-new-project

# Создать новый git репозиторий
rm -rf .git
git init
git remote add origin <your-new-repo-url>
```

---

## 🏷️ 2. Переименование проекта (5 мин)

### Быстрые изменения в коде

```bash
# 1. Переименовать Django app
mv backend/app backend/YOUR_PROJECT_NAME

# 2. Найти и заменить во всех файлах
find . -name "*.py" -o -name "*.toml" -o -name "*.json" -o -name "*.md" -o -name "Makefile" | \
xargs sed -i '' 's/boilerplate/YOUR_PROJECT_NAME/g'

find . -name "*.py" -o -name "*.toml" -o -name "*.json" -o -name "*.md" -o -name "Makefile" | \
xargs sed -i '' 's/app\./YOUR_PROJECT_NAME\./g'
```

### Обязательные файлы для ручного изменения

```bash
# Обновить эти файлы вручную:
vim backend/YOUR_PROJECT_NAME/settings/base.py  # ROOT_URLCONF, WSGI_APPLICATION
vim backend/YOUR_PROJECT_NAME/wsgi.py          # Django app reference  
vim backend/YOUR_PROJECT_NAME/asgi.py          # Django app reference
vim backend/manage.py                          # DJANGO_SETTINGS_MODULE
vim frontend/package.json                     # name, description
vim frontend/index.html                       # title
```

### Обновить конфигурации

```toml
# backend/pyproject.toml
[project]
name = "your-project-backend"
description = "Your project description"

[project.urls]
Homepage = "https://github.com/yourusername/your-project"
```

```json
# frontend/package.json
{
  "name": "your-project-frontend", 
  "description": "Your project frontend",
  "homepage": "https://your-domain.com"
}
```

---

## 🔧 3. Переменные окружения (3 мин)

### Backend

```bash
# Создать .env файл
cp .env.example .env

# Обновить ключевые переменные
vim .env
```

```bash
# .env - минимальные изменения
DJANGO_SECRET_KEY=your-unique-secret-key-generate-new-one
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
CORS_ALLOWED_ORIGINS=http://localhost:5173,https://your-domain.com

# DB и Redis можно оставить как есть для разработки
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/your_project_db
REDIS_URL=redis://localhost:6379/0
```

### Frontend

```bash
# Создать .env файл
cp frontend/.env.example frontend/.env

# Обновить API URL если нужно
vim frontend/.env
```

```bash
# frontend/.env
VITE_API_BASE=http://localhost:8000/api
VITE_ENVIRONMENT=development
```

---

## 🐳 4. Первый запуск (3 мин)

```bash
# Установить зависимости и запустить сервисы
make setup

# Запустить PostgreSQL и Redis
make services

# Применить миграции и создать суперпользователя  
make migrate
make superuser

# Запустить разработку
make dev
```

### Проверить что работает

- 🌐 **Frontend**: http://localhost:5173
- 🔧 **API**: http://localhost:8000/api  
- 👤 **Admin**: http://localhost:8000/admin
- 📊 **Health**: http://localhost:8000/api/health/

---

## 📝 5. Первый коммит (2 мин)

```bash
# Добавить все изменения
git add .

# Первый коммит
git commit -m "🎉 Initial setup from boilerplate

- Renamed project to YOUR_PROJECT_NAME
- Updated environment variables
- Configured for YOUR_DOMAIN.com
- Ready for development"

# Запушить в новый репозиторий
git branch -M main
git push -u origin main
```

---

## 🎯 Что дальше?

### Сразу после setup

1. **📱 Тест функциональности**
   - Войти как admin:admin123
   - Создать Echo задачу
   - Проверить theme toggle
   - Протестировать logout

2. **🧪 Запустить тесты**
   ```bash
   make test        # Все тесты
   make pre-commit  # Проверки качества кода
   ```

3. **🔒 Обновить credentials**
   - Сменить пароль admin пользователя
   - Сгенерировать новый SECRET_KEY
   - Настроить production переменные

### Следующие шаги

- 📖 **Изучить [ADAPTATION_GUIDE.md](ADAPTATION_GUIDE.md)** для детальной настройки
- 🔒 **Пройти [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)** для безопасности
- 🌐 **Настроить деплой** по [GCP_DEPLOYMENT.md](GCP_DEPLOYMENT.md)

---

## 🛠️ Кастомизация под ваш проект

### Добавление новых фичей

```bash
# Backend - создать новое Django приложение
cd backend
python manage.py startapp products

# Frontend - создать новую фичу (FSD-lite)
mkdir -p frontend/src/entities/product
mkdir -p frontend/src/features/product-list  
mkdir -p frontend/src/pages/products
```

### Обновление зависимостей

```bash
# Backend
cd backend
uv add django-extensions  # Пример новой зависимости

# Frontend  
cd frontend
pnpm add react-hook-form  # Пример новой зависимости
```

### Настройка API эндпоинтов

```python
# backend/YOUR_PROJECT_NAME/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Добавить ваши ViewSets в router
router = DefaultRouter()
# router.register(r'products', ProductViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('app.api.urls')),
    path('api/', include(router.urls)),  # Ваши новые API
]
```

---

## 🔍 Troubleshooting

### Частые проблемы при setup

1. **Port already in use**
   ```bash
   # Остановить все сервисы и перезапустить
   make docker-down
   make services
   ```

2. **Permission denied на миграциях**
   ```bash
   # Пересоздать БД
   make docker-down
   docker volume rm boilerplate_drf_celery_react_ts_postgres_data
   make services
   make migrate
   ```

3. **Frontend не подключается к API**
   ```bash
   # Проверить CORS настройки в .env
   CORS_ALLOWED_ORIGINS=http://localhost:5173
   ```

4. **Node.js/Python версии**
   ```bash
   # Убедиться в правильных версиях
   python --version   # 3.11+
   node --version     # 18+  
   uv --version       # latest
   pnpm --version     # latest
   ```

### Полезные команды

```bash
# Статус всех сервисов
make status

# Просмотр логов
make logs

# Очистка всех кэшей
make clean

# Пересборка всего проекта
make docker-down
make clean  
make setup
make dev
```

---

## 📋 Quick Checklist

После выполнения всех шагов убедитесь:

### ✅ Проект переименован
- [ ] Django app переименован
- [ ] package.json обновлен
- [ ] Все ссылки на старое название заменены

### ✅ Переменные настроены  
- [ ] .env файлы созданы
- [ ] SECRET_KEY уникальный
- [ ] Домены обновлены
- [ ] CORS настроен

### ✅ Все работает
- [ ] Backend запускается (localhost:8000)
- [ ] Frontend запускается (localhost:5173)
- [ ] API доступно (/api/health/)
- [ ] Админка работает (/admin)
- [ ] Аутентификация работает
- [ ] Тесты проходят

### ✅ Готово к разработке
- [ ] Первый коммит сделан
- [ ] Репозиторий создан и запушен
- [ ] Команда ознакомлена с проектом
- [ ] Следующие шаги запланированы

---

**🎉 Готово! Ваш проект настроен и готов к разработке!**

**Время setup: ~15 минут**
**Результат: Полностью функционирующий Django + React проект**

---

## 🔗 Что дальше

| Документ | Назначение | Время |
|----------|------------|-------|
| [ADAPTATION_GUIDE.md](ADAPTATION_GUIDE.md) | Детальная кастомизация | 2-4 часа |
| [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md) | Подготовка к продакшену | 1-2 часа |
| [GCP_DEPLOYMENT.md](GCP_DEPLOYMENT.md) | Деплой на Google Cloud | 3-6 часов |
| [before_commit.md](before_commit.md) | CI/CD и качество кода | 30 мин |

**Удачи с вашим проектом! 🚀**
