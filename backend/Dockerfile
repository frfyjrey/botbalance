# 🐍 Django + uv Production Dockerfile
FROM python:3.12-slim

# 🔧 Системные зависимости
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 📦 Установка uv
RUN pip install uv

# 👤 Создание non-root пользователя
RUN useradd --create-home --shell /bin/bash app
WORKDIR /app

# 📋 Копирование зависимостей
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 📁 Копирование кода
COPY --chown=app:app . .

# 🗂️ Статические файлы и права
RUN uv run python manage.py collectstatic --noinput
RUN chown -R app:app /app

# 👤 Переключение на non-root
USER app

# 🔧 Настройка PATH для использования .venv напрямую
ENV PATH="/app/.venv/bin:$PATH"

# 🌐 Открытие порта
EXPOSE 8080

# 🚀 Команда запуска с оптимизированными параметрами для Cloud Run
CMD ["sh", "-c", "gunicorn botbalance.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 120 --graceful-timeout 30 --keep-alive 65 --log-level info"]
