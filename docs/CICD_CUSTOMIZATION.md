# 🔄 CI/CD Customization Guide

Подробное руководство по настройке и адаптации CI/CD pipeline для вашего проекта.

---

## 📋 Текущая CI/CD архитектура

### GitHub Actions Workflows

- **🔧 `.github/workflows/ci.yml`** - Основной CI pipeline
- **🔒 `.github/workflows/security.yml`** - Security scanning
- **📦 `.github/dependabot.yml`** - Dependency updates

### Что покрывается

| Компонент | Backend | Frontend | Общее |
|-----------|---------|----------|-------|
| **Linting** | ruff, mypy | ESLint, Prettier | ✅ |
| **Testing** | pytest | vitest, playwright | ✅ |
| **Security** | bandit, safety | npm audit | CodeQL, GitLeaks |
| **Matrix** | Python 3.11/3.12 | Node 18/20/22 | ✅ |
| **Coverage** | pytest-cov | vitest | Codecov |

---

## 🛠️ Адаптация для нового проекта

### 1. Обновление базовых настроек

#### `.github/workflows/ci.yml`

```yaml
name: 🚀 CI Pipeline

env:
  # ✅ ОБНОВИТЬ: Основные переменные проекта
  PROJECT_NAME: "your-project-name"          # Изменить
  PYTHON_VERSION: "3.12"                     # По умолчанию ОК
  NODE_VERSION: "20"                         # По умолчанию ОК
  UV_VERSION: "latest"                       # По умолчанию ОК  
  PNPM_VERSION: "latest"                     # По умолчанию ОК

jobs:
  changes:
    # ... изменений не требует
    
  backend-tests-linux:
    env:
      # ✅ ОБНОВИТЬ: Django settings module
      DJANGO_SETTINGS_MODULE: your_project.settings.local  # Изменить
    # ... остальное без изменений
```

#### Обновите переменные в других местах

```bash
# Найти и заменить во всех workflow файлах
find .github -name "*.yml" | xargs sed -i '' 's/app\.settings\.local/your_project.settings.local/g'
find .github -name "*.yml" | xargs sed -i '' 's/boilerplate/your-project-name/g'
```

### 2. Настройка Dependabot

#### `.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
    reviewers:
      - "your-github-username"        # ✅ ОБНОВИТЬ
      - "your-team-lead"             # ✅ ДОБАВИТЬ
    assignees:
      - "your-github-username"        # ✅ ОБНОВИТЬ
    labels:
      - "dependencies"
      - "backend"
    open-pull-requests-limit: 5
    
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly" 
      day: "monday"
      time: "09:00"
    reviewers:
      - "your-github-username"        # ✅ ОБНОВИТЬ
    assignees:
      - "your-github-username"        # ✅ ОБНОВИТЬ
    labels:
      - "dependencies"
      - "frontend"
    open-pull-requests-limit: 5
```

### 3. Настройка секретов и переменных

#### Repository Secrets (Settings → Secrets and variables → Actions)

```bash
# Обязательные секреты для продакшена
CODECOV_TOKEN=your-codecov-token                    # Для coverage reports
DOCKER_HUB_TOKEN=your-dockerhub-token              # Если используете Docker Hub
GCP_SA_KEY=your-gcp-service-account-key            # Для GCP деплоя  
SENTRY_AUTH_TOKEN=your-sentry-token                # Для error tracking

# Для production деплоя
PRODUCTION_SECRET_KEY=your-production-secret
PRODUCTION_DATABASE_URL=your-production-db-url
PRODUCTION_REDIS_URL=your-production-redis-url
```

#### Repository Variables

```bash
# Публичные переменные
PROJECT_NAME=your-project-name
PRODUCTION_DOMAIN=your-domain.com
API_DOMAIN=api.your-domain.com
```

---

## 🚀 Добавление Deployment Workflow

### 1. Создание production deployment

```yaml
# .github/workflows/deploy-production.yml
name: 🚀 Deploy to Production

on:
  push:
    branches: [main]
    tags: ['v*']
  workflow_dispatch:  # Ручной запуск

env:
  PROJECT_ID: your-gcp-project-id           # ✅ ОБНОВИТЬ
  REGION: europe-west1                      # ✅ ВЫБРАТЬ РЕГИОН
  SERVICE_NAME: your-app-backend            # ✅ ОБНОВИТЬ

jobs:
  # Запускаем деплой только если CI прошел
  deploy:
    name: 🚀 Deploy to Production
    runs-on: ubuntu-latest
    needs: [backend-tests-linux, frontend-tests]  # Зависимость от CI
    if: github.ref == 'refs/heads/main'
    
    environment:
      name: production
      url: https://${{ vars.PRODUCTION_DOMAIN }}
    
    steps:
      - name: 📥 Checkout code
        uses: actions/checkout@v4

      - name: 🔐 Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: 🛠️ Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      # Backend deployment
      - name: 🐳 Build and deploy backend
        run: |
          cd backend
          gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME
          gcloud run deploy $SERVICE_NAME \
            --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
            --region $REGION \
            --platform managed \
            --allow-unauthenticated \
            --set-env-vars DJANGO_SETTINGS_MODULE=your_project.settings.prod

      # Frontend deployment  
      - name: 🌐 Deploy frontend
        run: |
          cd frontend
          npm ci
          VITE_API_BASE=https://${{ vars.API_DOMAIN }} npm run build
          gsutil -m rsync -r -d dist/ gs://your-frontend-bucket/

      # Smoke tests
      - name: 🧪 Production smoke tests
        run: |
          curl -f https://${{ vars.API_DOMAIN }}/api/health/ || exit 1
          curl -f https://${{ vars.PRODUCTION_DOMAIN }} || exit 1
```

### 2. Создание staging deployment

```yaml
# .github/workflows/deploy-staging.yml  
name: 🧪 Deploy to Staging

on:
  push:
    branches: [develop]
  pull_request:
    branches: [main]

env:
  PROJECT_ID: your-gcp-project-id-staging    # ✅ STAGING PROJECT
  REGION: europe-west1
  SERVICE_NAME: your-app-backend-staging

jobs:
  deploy-staging:
    name: 🧪 Deploy to Staging
    runs-on: ubuntu-latest
    if: github.event_name == 'push' || github.event.pull_request.head.repo.full_name == github.repository
    
    environment:
      name: staging
      url: https://staging.your-domain.com
    
    steps:
      # ... аналогично production но для staging окружения
```

---

## 🔧 Кастомизация под специфику проекта

### 1. Микросервисная архитектура

Если у вас несколько сервисов:

```yaml
# .github/workflows/ci-microservices.yml
jobs:
  changes:
    outputs:
      auth-service: ${{ steps.changes.outputs.auth-service }}
      user-service: ${{ steps.changes.outputs.user-service }}
      notification-service: ${{ steps.changes.outputs.notification-service }}
      
  auth-service-tests:
    needs: changes
    if: needs.changes.outputs.auth-service == 'true'
    # ... тесты для auth service
    
  user-service-tests:
    needs: changes  
    if: needs.changes.outputs.user-service == 'true'
    # ... тесты для user service
```

### 2. Дополнительные языки/технологии

#### Добавление Go сервиса

```yaml
go-tests:
  name: 🐹 Go Tests
  runs-on: ubuntu-latest
  needs: changes
  if: needs.changes.outputs.go-service == 'true'
  
  strategy:
    matrix:
      go-version: ['1.21', '1.22']
      
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-go@v5
      with:
        go-version: ${{ matrix.go-version }}
    
    - name: 🧪 Run tests
      working-directory: ./go-service
      run: |
        go mod download
        go test -v ./...
        go test -race ./...
```

#### Добавление Rust сервиса

```yaml
rust-tests:
  name: 🦀 Rust Tests  
  runs-on: ubuntu-latest
  needs: changes
  if: needs.changes.outputs.rust-service == 'true'
  
  steps:
    - uses: actions/checkout@v4
    - uses: dtolnay/rust-toolchain@stable
    
    - name: 🧪 Run tests
      working-directory: ./rust-service  
      run: |
        cargo test
        cargo clippy -- -D warnings
        cargo fmt -- --check
```

### 3. Специализированные тесты

#### Performance Testing

```yaml
performance-tests:
  name: ⚡ Performance Tests
  runs-on: ubuntu-latest
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  
  steps:
    - uses: actions/checkout@v4
    
    - name: 🚀 Setup test environment
      run: |
        docker-compose -f docker-compose.perf.yml up -d
        
    - name: ⚡ Run load tests
      run: |
        npm install -g artillery
        artillery run performance/load-test.yml
        
    - name: 📊 Upload results
      uses: actions/upload-artifact@v4
      with:
        name: performance-results
        path: performance/results/
```

#### Security Testing

```yaml
security-tests:
  name: 🔒 Security Tests
  runs-on: ubuntu-latest
  
  steps:
    - uses: actions/checkout@v4
    
    - name: 🕷️ OWASP ZAP Scan
      uses: zaproxy/action-full-scan@v0.10.0
      with:
        target: 'https://staging.your-domain.com'
        
    - name: 🔍 Docker Image Scan
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: 'gcr.io/${{ env.PROJECT_ID }}/your-app'
        format: 'sarif'
        output: 'trivy-results.sarif'
```

---

## 🎯 Оптимизация производительности CI

### 1. Кэширование зависимостей

#### Backend (Python/uv)

```yaml
- name: 💾 Cache Python dependencies
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/uv
      backend/.venv
    key: ${{ runner.os }}-python-${{ matrix.python-version }}-${{ hashFiles('backend/uv.lock') }}
    restore-keys: |
      ${{ runner.os }}-python-${{ matrix.python-version }}-
      ${{ runner.os }}-python-
```

#### Frontend (Node.js/pnpm)

```yaml
- name: 💾 Cache Node dependencies
  uses: actions/cache@v4  
  with:
    path: |
      ~/.pnpm-store
      frontend/node_modules
    key: ${{ runner.os }}-pnpm-${{ hashFiles('frontend/pnpm-lock.yaml') }}
    restore-keys: |
      ${{ runner.os }}-pnpm-
```

### 2. Параллелизация тестов

```yaml
backend-tests:
  strategy:
    fail-fast: false
    matrix:
      python-version: ['3.11', '3.12']
      test-group: [unit, integration, e2e]
      
  steps:
    - name: 🧪 Run tests
      run: |
        case ${{ matrix.test-group }} in
          unit)
            uv run pytest tests/unit/ --maxfail=1
            ;;
          integration)  
            uv run pytest tests/integration/ --maxfail=1
            ;;
          e2e)
            uv run pytest tests/e2e/ --maxfail=1
            ;;
        esac
```

### 3. Условное выполнение

```yaml
# Запускать тяжелые тесты только на main/develop
heavy-tests:
  if: contains(fromJSON('["main", "develop"]'), github.ref_name)
  
# Пропускать тесты если только документация изменилась
backend-tests:
  if: needs.changes.outputs.backend == 'true' || needs.changes.outputs.docs == 'false'
```

---

## 📊 Мониторинг и уведомления

### 1. Slack интеграция

```yaml
- name: 📢 Notify Slack on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: failure
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
    text: |
      🚨 CI Pipeline Failed
      Branch: ${{ github.ref }}
      Author: ${{ github.actor }}
      Commit: ${{ github.sha }}
```

### 2. Email уведомления

```yaml
- name: 📧 Send email on deployment  
  if: success() && github.ref == 'refs/heads/main'
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.your-domain.com
    server_port: 587
    username: ${{ secrets.EMAIL_USERNAME }}
    password: ${{ secrets.EMAIL_PASSWORD }}
    subject: "🚀 Production Deployment Successful"
    body: |
      Production deployment completed successfully!
      
      Commit: ${{ github.sha }}
      Author: ${{ github.actor }}
      Time: ${{ github.event.head_commit.timestamp }}
```

### 3. GitHub Deployments API

```yaml
- name: 📝 Create deployment
  uses: chrnorm/deployment-action@v2
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    environment-url: https://${{ vars.PRODUCTION_DOMAIN }}
    environment: production
    description: "Deployed commit ${{ github.sha }}"
```

---

## 🛡️ Security и compliance

### 1. Подписывание коммитов

```yaml
- name: ✍️ Verify commit signature
  run: |
    git verify-commit HEAD || {
      echo "❌ Commit not signed"
      exit 1
    }
```

### 2. SBOM Generation

```yaml
- name: 📋 Generate SBOM
  uses: anchore/sbom-action@v0
  with:
    path: ./
    format: spdx-json
    
- name: 📤 Upload SBOM
  uses: actions/upload-artifact@v4
  with:
    name: sbom
    path: sbom.spdx.json
```

### 3. Compliance проверки

```yaml
- name: 🏛️ SOX Compliance Check
  run: |
    # Проверка что изменения прошли review
    if [ "${{ github.event.pull_request.reviews }}" == "null" ]; then
      echo "❌ Changes must be reviewed for SOX compliance"
      exit 1
    fi
```

---

## 📋 Checklist адаптации CI/CD

### ✅ Базовая настройка

- [ ] Обновлены переменные проекта в workflows
- [ ] Изменены пути к Django settings
- [ ] Настроены секреты в GitHub
- [ ] Обновлен Dependabot config
- [ ] Протестирована работа CI на test commit

### ✅ Продвинутая настройка

- [ ] Добавлен deployment workflow
- [ ] Настроены окружения (staging/production)
- [ ] Добавлены уведомления (Slack/Email)
- [ ] Настроено кэширование для ускорения
- [ ] Добавлены специфичные для проекта тесты

### ✅ Security & Compliance

- [ ] Включены security scans
- [ ] Настроены compliance проверки  
- [ ] Добавлена генерация SBOM
- [ ] Проверена подписка коммитов
- [ ] Настроен мониторинг безопасности

---

## 🚀 Готовые примеры для разных сценариев

### Монорепозиторий

```yaml
# Определение изменений для монорепо
jobs:
  changes:
    outputs:
      backend: ${{ steps.changes.outputs.backend }}
      frontend: ${{ steps.changes.outputs.frontend }}
      mobile: ${{ steps.changes.outputs.mobile }}
      docs: ${{ steps.changes.outputs.docs }}
    steps:
      - uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            backend:
              - 'backend/**'
              - 'shared/backend/**'
            frontend:
              - 'frontend/**'  
              - 'shared/frontend/**'
            mobile:
              - 'mobile/**'
            docs:
              - 'docs/**'
              - '*.md'
```

### Мультисервисная архитектура

```yaml
# Матричное тестирование сервисов
strategy:
  matrix:
    service: [auth, users, orders, payments, notifications]
    
steps:
  - name: 🧪 Test ${{ matrix.service }} service
    working-directory: ./services/${{ matrix.service }}
    run: |
      make test
      make lint
```

---

**🎉 Готово! Ваша CI/CD pipeline адаптирована под ваш проект!**

**Помните**: CI/CD это живой процесс. Регулярно пересматривайте и оптимизируйте ваши workflows по мере роста проекта.
