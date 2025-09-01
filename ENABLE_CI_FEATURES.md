# 🔄 Включение отключенных CI/CD функций

**⚠️ ВРЕМЕННО ОТКЛЮЧЕНЫ для активного деплоя:**

## 🎭 E2E тесты
Отключены в `.github/workflows/ci.yml` строка 246

**Как включить обратно:**
```yaml
# УБРАТЬ эту строку:
if: false  # ВРЕМЕННО ОТКЛЮЧЕНЫ - убрать эту строку чтобы включить обратно

# ВЕРНУТЬ исходное условие:  
if: |
  always() && 
  (needs.backend-tests-linux.result == 'success' || needs.backend-tests-linux.result == 'skipped') &&
  (needs.frontend-tests.result == 'success' || needs.frontend-tests.result == 'skipped') &&
  (github.event.inputs.run_e2e == 'true' || github.event.inputs.run_e2e == '' || github.event_name != 'workflow_dispatch')
```

## 🤖 Dependabot
Отключен переименованием файла `.github/dependabot.yml.disabled`

**Как включить обратно:**
```bash
mv .github/dependabot.yml.disabled .github/dependabot.yml
```

---

**❗ НЕ ЗАБЫТЬ ВКЛЮЧИТЬ ОБРАТНО ПОСЛЕ ДЕПЛОЯ!**

