# Продакшен исправления для BotBalance

## 🚨 Критические исправления (уже внесены в код)

### 1. Redis CONNECTION проблема
**Проблема**: `TypeError: AbstractConnection.init() got an unexpected keyword argument 'CLIENT_CLASS'`  
**Исправление**: Убрана опция `CLIENT_CLASS` из настроек Redis в `prod.py`

```python
# БЫЛО (не работало):
"OPTIONS": {
    "CLIENT_CLASS": "django_redis.client.DefaultClient",  # ← Это вызывало ошибку
    "CONNECTION_POOL_KWARGS": {...}
}

# СТАЛО (работает):
"OPTIONS": {
    "CONNECTION_POOL_KWARGS": {...}
}
```

### 2. Django админка без статики
**Проблема**: 500 ошибки при входе в админку, отсутствует CSS/JS  
**Исправления**:
- ✅ Добавлена зависимость `whitenoise>=6.6.0` в `pyproject.toml`
- ✅ Добавлен `WhiteNoiseMiddleware` в `prod.py`
- ✅ Настроен `STATICFILES_STORAGE` для сжатия статики
- ✅ Исправлены пути статических файлов

### 3. CORS пустые origins
**Проблема**: `corsheaders.E013: Origin '' in CORS_ALLOWED_ORIGINS`  
**Исправление**: Безопасная обработка переменных окружения

```python
# Теперь безопасно обрабатывает пустые переменные
if os.getenv("CORS_ALLOWED_ORIGINS"):
    CORS_ALLOWED_ORIGINS.extend(
        origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") 
        if origin.strip()
    )
```

## 🚀 Как задеплоить исправления

### 1. Обновить зависимости
```bash
# В контейнере или на сервере
pip install whitenoise>=6.6.0
```

### 2. Собрать статику
```bash
python manage.py collectstatic --noinput
```

### 3. Перезапустить сервисы
- Перезапустить Django приложение
- Перезапустить Celery workers (чтобы подхватить новые настройки Redis)

### 4. Проверить работу
- Админка: https://api.botbalance.me/nukoadmin/ (должна иметь стили)
- API: https://api.botbalance.me/api/health/ (должен отвечать без ошибок Redis)

## 📊 Результат
- ✅ Redis подключения работают
- ✅ Django админка доступна со стилями  
- ✅ Статические файлы сервятся через Whitenoise
- ✅ API endpoints работают корректно
- ✅ Все тесты проходят (62 backend + 6 frontend)

## 🔧 Дополнительные улучшения
- Создана директория `backend/static/` для разработки
- Исправлена обработка переменных окружения CORS и ALLOWED_HOSTS
- Унифицированы пути статических файлов (используется pathlib)
