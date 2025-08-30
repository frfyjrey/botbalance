# 🚀 Pre-commit Checklist 

**ОБЯЗАТЕЛЬНО выполнять перед КАЖДЫМ коммитом!** 

## 📋 Быстрый способ - автоматический скрипт

```bash
# Запустить все проверки одной командой
# ✨ Скрипт АВТОМАТИЧЕСКИ исправляет все что можно!
./pre-commit-check.sh

# Или через Makefile  
make pre-commit
```

**🎯 Что делает скрипт:**
1. **Автоисправление**: форматирование, простые линтинг ошибки
2. **Проверки**: типы, тесты, билды - то что требует ручного исправления

---

## 🔧 Ручные команды (если что-то не работает)

### **Backend проверки:**

```bash
# Перейти в backend
cd backend

# 1. Обновить зависимости
uv sync --dev

# 2. 🔧 АВТОИСПРАВЛЕНИЕ (сначала исправляем все что можно)
uv run ruff format .                    # Исправить форматирование
uv run ruff check --fix .               # Автоисправить линтинг

# 3. ✅ ПРОВЕРКИ (потом проверяем что осталось)  
uv run ruff check .                     # Проверить оставшиеся проблемы
uv run mypy .                           # Проверить типы
DJANGO_SETTINGS_MODULE=app.settings.local uv run pytest --no-cov -v    # Тесты
DJANGO_SETTINGS_MODULE=app.settings.local uv run python manage.py check --deploy    # Django система
DJANGO_SETTINGS_MODULE=app.settings.local uv run python manage.py makemigrations --check --dry-run    # Миграции
```

### **Frontend проверки:**

```bash
# Перейти в frontend
cd ../frontend

# 1. Обновить зависимости
pnpm install --frozen-lockfile

# 2. 🔧 АВТОИСПРАВЛЕНИЕ (сначала исправляем все что можно)
pnpm format                             # Исправить форматирование
pnpm lint:fix                           # Автоисправить ESLint

# 3. ✅ ПРОВЕРКИ (потом проверяем что осталось)
pnpm lint                               # Проверить ESLint + TypeScript
pnpm format:check                       # Проверить форматирование
pnpm test:run                           # Запустить тесты
pnpm build                              # Проверить production build

# 4. E2E тесты (опционально)
pnpm test:e2e --headed=false
```

---

## ⚠️ Важные переменные окружения

### **Backend Django команды ВСЕГДА с настройками:**
```bash
# ❌ НЕПРАВИЛЬНО - падает с ошибкой
uv run pytest

# ✅ ПРАВИЛЬНО  
DJANGO_SETTINGS_MODULE=app.settings.local uv run pytest

# ❌ НЕПРАВИЛЬНО
uv run python manage.py check

# ✅ ПРАВИЛЬНО
DJANGO_SETTINGS_MODULE=app.settings.local uv run python manage.py check
```

---

## 🛠️ Исправление частых ошибок

### **Django ImproperlyConfigured:**
```bash
# Если видите: "settings are not configured"
# ВСЕГДА добавляйте DJANGO_SETTINGS_MODULE
DJANGO_SETTINGS_MODULE=app.settings.local [ваша команда]
```

### **Ruff форматирование:**
```bash
# Если ruff format --check падает
cd backend
uv run ruff format .  # автоисправление
```

### **ESLint ошибки:**
```bash
# Если eslint падает
cd frontend
pnpm lint --fix  # автоисправление
pnpm format      # исправить prettier
```

### **TypeScript ошибки:**
```bash
# Проверить типы
cd frontend  
pnpm type-check

# Если есть ошибки - исправить в коде
```

### **Build ошибки:**
```bash
# Проверить что production build работает
cd frontend
pnpm build

# Если падает - исправить ошибки в коде
```

---

## 🎯 Минимальный набор (если спешите)

```bash
# 1. Backend - исправить + проверить
cd backend
uv run ruff format . && uv run ruff check --fix . && uv run ruff check .
DJANGO_SETTINGS_MODULE=app.settings.local uv run pytest --no-cov -q

# 2. Frontend - исправить + проверить  
cd ../frontend
pnpm format && pnpm lint:fix && pnpm lint && pnpm test:run

# 3. Проверить что нет незакоммиченных файлов
git status
```

---

## ✅ Готово к коммиту!

Если все команды прошли ✅ - можно коммитить:

```bash
git add .
git commit -m "Ваше сообщение"
git push
```