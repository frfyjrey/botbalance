#!/bin/bash

# 🔧 Pre-commit Quality Checks
# Run this script before EVERY commit to avoid CI/CD failures!

set -e  # Exit on any error

echo "🚀 Starting Pre-commit Checks..."

# Check if we're in project root
if [ ! -f "pyproject.toml" ] && [ ! -d "backend" ]; then
    echo "❌ Run this script from project root!"
    exit 1
fi

# =====================================
# 🔧 BACKEND CHECKS
# =====================================
echo ""
echo "🔧 Backend Checks..."
cd backend

echo "  📋 Installing/updating backend dependencies..."
uv sync --dev

echo "  🔧 Auto-fixing backend code..."
echo "    🎨 Formatting with ruff..."
uv run ruff format .
echo "    🔍 Auto-fixing linting issues..."
uv run ruff check --fix .

echo "  ✅ Final backend checks..."
echo "    🔍 Checking remaining linting issues..."
uv run ruff check .
echo "    🔍 Running mypy type checking..."
uv run mypy .

echo "  🧪 Running backend tests..."
DJANGO_SETTINGS_MODULE=botbalance.settings.local uv run pytest --no-cov --disable-warnings -q

echo "  ✅ Django system checks..."
DJANGO_SETTINGS_MODULE=botbalance.settings.local uv run python manage.py check --deploy

echo "  ✅ Django migration checks..."
DJANGO_SETTINGS_MODULE=botbalance.settings.local uv run python manage.py makemigrations --check --dry-run

# =====================================
# ⚛️ FRONTEND CHECKS  
# =====================================
echo ""
echo "⚛️ Frontend Checks..."
cd ../frontend

echo "  📋 Installing/updating frontend dependencies..."
pnpm install --frozen-lockfile

echo "  🔧 Auto-fixing frontend code..."
echo "    🎨 Formatting with Prettier..."
pnpm format
echo "    🔍 Auto-fixing ESLint issues..."
pnpm lint:fix

echo "  ✅ Final frontend checks..."
echo "    🔍 Checking ESLint + TypeScript..."
pnpm lint
echo "    🎨 Verifying Prettier formatting..."
pnpm format:check

echo "  🧪 Running frontend tests..."
pnpm test:run

echo "  📦 Testing production build..."
pnpm build

# =====================================
# 🛡️ GENERAL CHECKS
# =====================================
echo ""
echo "🛡️ General Checks..."
cd ..

echo "  📊 Git status check..."
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Warning: You have unstaged changes!"
    git status --short
fi

echo "  🐳 Docker Compose validation..."
docker-compose config > /dev/null

echo "  🔨 Makefile validation..."
make --dry-run help > /dev/null

# =====================================
# ✅ SUCCESS
# =====================================
echo ""
echo "🎉 ALL CHECKS PASSED!"
echo "✅ Safe to commit and push!"
echo ""
echo "Commands you can run now:"
echo "  git add ."
echo "  git commit -m 'Your commit message'"
echo "  git push"
