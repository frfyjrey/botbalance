# 🔒 Security Checklist

Комплексный чек-лист безопасности для подготовки Django + React приложения к продакшену.

---

## 📋 Основные принципы

- ✅ **Defense in Depth** - многоуровневая защита
- ✅ **Principle of Least Privilege** - минимальные права доступа  
- ✅ **Security by Design** - безопасность с самого начала
- ✅ **Regular Security Audits** - регулярные проверки

---

## 🛡️ Backend Security (Django)

### Django Settings

#### Обязательные настройки

- [ ] **`DEBUG = False`** в продакшене
- [ ] **`SECRET_KEY`** - уникальный, сложный, из переменных окружения
- [ ] **`ALLOWED_HOSTS`** - только нужные домены
- [ ] **`SECURE_SSL_REDIRECT = True`** - принудительный HTTPS
- [ ] **`SECURE_HSTS_SECONDS = 31536000`** - HSTS на год
- [ ] **`SECURE_HSTS_INCLUDE_SUBDOMAINS = True`**
- [ ] **`SECURE_HSTS_PRELOAD = True`**

```python
# backend/your_project/settings/prod.py
DEBUG = False
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']  # Никогда в коде!
ALLOWED_HOSTS = ['api.your-domain.com', 'your-domain.com']

# HTTPS Security
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 год
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

#### Куки и сессии

- [ ] **`SESSION_COOKIE_SECURE = True`** - только HTTPS
- [ ] **`SESSION_COOKIE_HTTPONLY = True`** - защита от XSS
- [ ] **`CSRF_COOKIE_SECURE = True`** - CSRF куки только HTTPS
- [ ] **`CSRF_COOKIE_HTTPONLY = True`** - защита CSRF токенов
- [ ] **`SESSION_COOKIE_SAMESITE = 'Strict'`** - защита от CSRF

```python
# Безопасные куки
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
```

#### CORS настройки

- [ ] **`CORS_ALLOWED_ORIGINS`** - только нужные домены
- [ ] **`CORS_ALLOW_CREDENTIALS = True`** если нужны куки
- [ ] **Без `CORS_ALLOW_ALL_ORIGINS = True`** в продакшене

```python
# Строгие CORS настройки
CORS_ALLOWED_ORIGINS = [
    'https://your-domain.com',
    'https://botbalance.your-domain.com',
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_HEADERS = [
    'authorization',
    'content-type',
    'x-csrftoken',
]
```

### Database Security

- [ ] **Отдельный пользователь БД** с минимальными правами
- [ ] **Сложный пароль БД** (сгенерированный)
- [ ] **SSL соединение** с базой данных
- [ ] **Регулярные бэкапы** с шифрованием
- [ ] **Ротация паролей** БД каждые 90 дней

```python
# Безопасное подключение к БД
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'sslmode': 'require',  # SSL обязательно
            'options': '-c default_transaction_isolation=serializable'
        },
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
    }
}
```

### API Security

- [ ] **JWT токены** с коротким TTL
- [ ] **Refresh токены** с ротацией
- [ ] **Rate limiting** на критических эндпоинтах
- [ ] **Input validation** на всех входных данных
- [ ] **API версионирование** для совместимости

```python
# JWT настройки
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),  # Короткий TTL
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,  # Ротация refresh токенов
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Rate limiting
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login': '5/min',  # Ограничение на логин
    }
}
```

### File Upload Security

- [ ] **Ограничение размера файлов**
- [ ] **Валидация типов файлов**
- [ ] **Сканирование на вирусы**
- [ ] **Отдельное хранилище** для загрузок

```python
# Безопасная загрузка файлов
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Разрешенные типы файлов
ALLOWED_FILE_TYPES = [
    'image/jpeg', 'image/png', 'image/gif',
    'application/pdf', 'text/plain'
]
```

---

## 🌐 Frontend Security (React)

### Content Security Policy

- [ ] **Строгий CSP** заголовок
- [ ] **nonce** для inline скриптов
- [ ] **Запрет eval()** и unsafe-inline

```html
<!-- CSP метатег или HTTP заголовок -->
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; 
               script-src 'self' 'nonce-random123'; 
               style-src 'self' 'unsafe-inline'; 
               img-src 'self' data: https:; 
               connect-src 'self' https://api.your-domain.com;">
```

### Environment Variables

- [ ] **Нет секретов** в frontend переменных
- [ ] **API URLs** через переменные окружения
- [ ] **Валидация** переменных при сборке

```typescript
// frontend/src/shared/config/env.ts
const requiredEnvVars = [
  'VITE_API_BASE',
  'VITE_ENVIRONMENT'
] as const;

// Валидация обязательных переменных
requiredEnvVars.forEach(envVar => {
  if (!import.meta.env[envVar]) {
    throw new Error(`Missing required environment variable: ${envVar}`);
  }
});

export const config = {
  apiBase: import.meta.env.VITE_API_BASE,
  environment: import.meta.env.VITE_ENVIRONMENT,
  // НЕ ДОБАВЛЯЙТЕ СЕКРЕТЫ СЮДА!
} as const;
```

### XSS Protection

- [ ] **React XSS защита** (dangerouslySetInnerHTML только при необходимости)
- [ ] **Валидация** пользовательского ввода
- [ ] **Санитизация** HTML контента
- [ ] **Использование** textContent вместо innerHTML

```typescript
// ❌ Опасно
element.innerHTML = userInput;

// ✅ Безопасно
element.textContent = userInput;

// ✅ Для HTML - используйте библиотеку санитизации
import DOMPurify from 'dompurify';
element.innerHTML = DOMPurify.sanitize(userInput);
```

### Local Storage Security

- [ ] **Нет JWT токенов** в localStorage (используйте httpOnly cookies)
- [ ] **Очистка** чувствительных данных при логауте
- [ ] **Шифрование** чувствительных данных в storage

```typescript
// ❌ Небезопасно - JWT в localStorage
localStorage.setItem('token', jwt);

// ✅ Безопасно - используйте httpOnly cookies для JWT
// Или храните в памяти с периодическим обновлением

// Для других данных - очистка при логауте
const logout = () => {
  localStorage.clear();
  sessionStorage.clear();
  // Дополнительная очистка состояния
};
```

---

## 🔐 Infrastructure Security

### Server Configuration

- [ ] **Обновления ОС** и пакетов
- [ ] **Firewall** настроен
- [ ] **SSH ключи** вместо паролей
- [ ] **Отключен root login** по SSH
- [ ] **Fail2ban** для защиты от брутфорса

### Docker Security

- [ ] **Non-root пользователь** в контейнерах
- [ ] **Minimal base images** (alpine, distroless)
- [ ] **No secrets** в Dockerfile или образах
- [ ] **Security scanning** образов
- [ ] **Read-only** файловая система где возможно

```dockerfile
# ✅ Безопасный Dockerfile
FROM python:3.12-slim

# Создание non-root пользователя
RUN useradd --create-home --shell /bin/bash app
WORKDIR /app

# Установка зависимостей как root
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копирование кода и смена владельца
COPY --chown=app:app . .

# Переключение на non-root пользователя
USER app

EXPOSE 8000
```

### TLS/SSL Configuration

- [ ] **TLS 1.2+** минимум (лучше TLS 1.3)
- [ ] **Strong cipher suites** только
- [ ] **Perfect Forward Secrecy** (PFS)
- [ ] **OCSP Stapling** включен
- [ ] **Certificate Transparency** мониторинг

### Load Balancer Security

- [ ] **Rate limiting** на уровне LB
- [ ] **DDoS protection** включена
- [ ] **WAF правила** настроены
- [ ] **IP whitelist** для админки
- [ ] **Geo-blocking** если нужно

---

## 📊 Monitoring & Logging

### Security Monitoring

- [ ] **Логирование** всех попыток аутентификации
- [ ] **Алерты** на подозрительную активность
- [ ] **Мониторинг** изменений в критических файлах
- [ ] **SIEM интеграция** если возможно

```python
# Логирование безопасности
LOGGING = {
    'version': 1,
    'handlers': {
        'security': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/security.log',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security'],
            'level': 'INFO',
        },
        'authentication': {
            'handlers': ['security'],  
            'level': 'INFO',
        },
    },
}

# В views логируйте критические события
import logging
security_logger = logging.getLogger('authentication')

def login(request):
    # ... логика логина ...
    if success:
        security_logger.info(f'Successful login: {username} from {request.META.get("REMOTE_ADDR")}')
    else:
        security_logger.warning(f'Failed login attempt: {username} from {request.META.get("REMOTE_ADDR")}')
```

### Error Handling

- [ ] **Не раскрывайте** техническую информацию в ошибках
- [ ] **Generic error messages** для пользователей
- [ ] **Детальное логирование** ошибок для разработчиков
- [ ] **Rate limiting** на эндпоинтах с ошибками

```python
# ✅ Безопасная обработка ошибок
def api_view(request):
    try:
        # ... бизнес логика ...
        pass
    except SpecificError as e:
        logger.error(f'Specific error in api_view: {e}', exc_info=True)
        return JsonResponse({'error': 'Operation failed'}, status=400)
    except Exception as e:
        logger.error(f'Unexpected error in api_view: {e}', exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)
```

---

## 🔧 Dependencies & Updates

### Dependency Management

- [ ] **Dependabot** или аналог для автообновлений
- [ ] **Vulnerability scanning** зависимостей
- [ ] **License compliance** проверка
- [ ] **Regular updates** критических пакетов

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
    reviewers:
      - "security-team"
    assignees:
      - "lead-dev"
    open-pull-requests-limit: 5
    
  - package-ecosystem: "npm"
    directory: "/frontend"  
    schedule:
      interval: "weekly"
    reviewers:
      - "security-team"
```

### Security Scanning

- [ ] **SAST** (Static Application Security Testing)
- [ ] **DAST** (Dynamic Application Security Testing)  
- [ ] **SCA** (Software Composition Analysis)
- [ ] **Container scanning** для уязвимостей

```yaml
# .github/workflows/security.yml
- name: Run SAST with CodeQL
  uses: github/codeql-action/analyze@v3
  
- name: Run dependency check
  uses: dependency-check/Dependency-Check_Action@main
  
- name: Run container scan
  uses: aquasecurity/trivy-action@master
```

---

## 🚨 Incident Response

### Preparation

- [ ] **Incident response plan** документирован
- [ ] **Contact list** актуален
- [ ] **Backup procedures** протестированы
- [ ] **Recovery procedures** документированы

### Detection

- [ ] **Automated alerts** настроены
- [ ] **Log monitoring** работает
- [ ] **Anomaly detection** включена
- [ ] **User reporting** процедура есть

### Response

- [ ] **Isolation procedures** готовы
- [ ] **Communication plan** есть
- [ ] **Forensic tools** доступны
- [ ] **Legal contacts** известны

---

## 📋 Pre-Production Checklist

### 🔒 Security Tests

- [ ] **Penetration testing** проведен
- [ ] **Vulnerability assessment** выполнен
- [ ] **OWASP Top 10** проверен
- [ ] **Code review** проведен security командой

### 🛡️ Configuration Review

- [ ] **All items** в этом чеклисте проверены
- [ ] **Security headers** настроены
- [ ] **Error pages** не раскрывают информацию
- [ ] **Debug mode** отключен везде

### 📊 Monitoring Setup

- [ ] **Security monitoring** настроен
- [ ] **Alerting** работает
- [ ] **Log aggregation** настроен
- [ ] **Incident response** готов

---

## 🔗 Useful Tools

### Security Scanners

- [**Safety**](https://pyup.io/safety/) - Python dependency scanner
- [**npm audit**](https://docs.npmjs.com/cli/v8/commands/npm-audit) - Node.js dependency scanner
- [**Bandit**](https://bandit.readthedocs.io/) - Python SAST scanner
- [**ESLint Security**](https://github.com/nodesecurity/eslint-plugin-security) - JavaScript security linter

### Security Headers

- [**SecurityHeaders.com**](https://securityheaders.com/) - Headers scanner
- [**Mozilla Observatory**](https://observatory.mozilla.org/) - Security assessment
- [**SSL Labs**](https://www.ssllabs.com/ssltest/) - SSL configuration test

### Penetration Testing

- [**OWASP ZAP**](https://www.zaproxy.org/) - Web application scanner
- [**Burp Suite**](https://portswigger.net/burp) - Professional web security testing
- [**Nmap**](https://nmap.org/) - Network discovery and security auditing

---

## 📚 Resources

### OWASP Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [OWASP Django Security](https://cheatsheetseries.owasp.org/cheatsheets/Django_Security_Cheat_Sheet.html)

### Security Guidelines

- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [React Security](https://reactjs.org/docs/dom-elements.html#dangerouslysetinnerhtml)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**🔒 Безопасность - это процесс, а не состояние. Регулярно пересматривайте и обновляйте эти настройки!**

> **Помните:** Этот чеклист покрывает основные аспекты безопасности, но не является исчерпывающим. Всегда консультируйтесь с экспертами по безопасности для критически важных приложений.
