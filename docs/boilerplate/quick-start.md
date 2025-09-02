# 🚀 Quick Start - Локальная разработка

> **Цель:** Запустить проект локально за 5 минут и проверить что все работает.

## 📋 **Что получишь:**
- ✅ Django API на http://localhost:8000
- ✅ React фронт на http://localhost:5173  
- ✅ PostgreSQL + Redis в Docker
- ✅ Celery worker для асинхронных задач
- ✅ Все тесты проходят

## 🔧 **Требования:**
- Python 3.11+ 
- Node.js 18+
- Docker + Docker Compose
- Make (обычно предустановлен)

## 📦 **1. Клонирование:**
```bash
git clone https://github.com/your-username/your-project.git
cd your-project
```

## ⚙️ **2. Настройка окружения:**

### Backend (.env файл):
```bash
cp env.example .env
# Отредактируй .env если нужны другие порты/настройки
```

### Frontend (.env файлы):
```bash
cd frontend
cp .env.example .env.local
# .env.local уже настроен для локальной разработки
cd ..
```

## 🚀 **3. Запуск всего стека:**
```bash
# Запускает ВСЕ сервисы (DB, Redis, Backend, Frontend, Celery)
make start

# Дождись сообщения "All services are running!"
# Обычно занимает 2-3 минуты при первом запуске
```

## ✅ **4. Проверка работоспособности:**

### Проверь эндпоинты:
- **API Health:** http://localhost:8000/api/health/
- **API Root:** http://localhost:8000/ 
- **Frontend:** http://localhost:5173
- **Django Admin:** http://localhost:8000/nukoadmin/ 

> Создай суперпользователя: `make createsuperuser`

### Тестирование:
```bash
# Полная проверка качества кода
make pre-commit

# Только backend тесты  
make test-backend

# Только frontend тесты
make test-frontend
```

## 📱 **5. Тестируй Celery задачи:**
1. Открой фронт: http://localhost:5173
2. Авторизуйся с созданным суперпользователем  
3. Создай тестовую задачу
4. Проверь что она выполнилась

## 🔄 **6. Полезные команды:**
```bash
make stop          # Остановить все сервисы
make clean          # Очистить Docker volumes/images  
make logs-backend   # Логи Django
make logs-worker    # Логи Celery worker
make shell-backend  # Django shell
```

## 🐛 **Типичные проблемы:**

### "Port already in use"
```bash
make stop
# Или найди и убей процесс:
lsof -ti:8000 | xargs kill -9
```

### "Database connection failed"  
```bash
# Пересоздай контейнеры:
make clean
make start
```

### Тесты не проходят
```bash
# Сброси тестовую БД:
make clean-db
make test-backend
```

---

## 🎯 **Готов к разработке!**
Если все эндпоинты отвечают и тесты проходят - можешь начинать кодить!

**Следующий шаг:** [Адаптация под твой проект](customization.md)
