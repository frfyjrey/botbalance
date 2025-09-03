#!/usr/bin/env python3
"""
🔍 Django Apps Consistency Checker

Проверяет консистентность INSTALLED_APPS между разными settings файлами
и автоматически обнаруживает потенциальные проблемы с отсутствующими приложениями.

Запуск: python check_django_apps.py
"""

import ast
import sys
from pathlib import Path


def extract_installed_apps(settings_file: Path) -> list[str]:
    """Извлекает INSTALLED_APPS из Python файла настроек."""
    try:
        with open(settings_file) as f:
            content = f.read()

        # Parse Python AST
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "INSTALLED_APPS":
                        if isinstance(node.value, ast.List):
                            apps = []
                            for item in node.value.elts:
                                if isinstance(item, ast.Constant) and isinstance(
                                    item.value, str
                                ):
                                    apps.append(item.value)
                            return apps
        return []
    except Exception as e:
        print(f"❌ Error parsing {settings_file}: {e}")
        return []


def find_apps_with_models() -> list[str]:
    """Находит все Django приложения с models.py файлами."""
    apps_with_models = []
    project_root = Path(__file__).parent / "botbalance"

    for app_dir in project_root.iterdir():
        if app_dir.is_dir() and not app_dir.name.startswith("_"):
            models_file = app_dir / "models.py"
            if models_file.exists():
                # Check if models.py has actual model definitions
                try:
                    with open(models_file) as f:
                        content = f.read()

                    # Simple check for Django models
                    if "models.Model" in content:
                        app_name = f"botbalance.{app_dir.name}"
                        apps_with_models.append(app_name)
                except Exception:
                    continue

    return apps_with_models


def find_apps_with_migrations() -> list[str]:
    """Находит все Django приложения с migrations папками."""
    apps_with_migrations = []
    project_root = Path(__file__).parent / "botbalance"

    for app_dir in project_root.iterdir():
        if app_dir.is_dir() and not app_dir.name.startswith("_"):
            migrations_dir = app_dir / "migrations"
            if migrations_dir.exists() and migrations_dir.is_dir():
                # Check if migrations dir has migration files (not just __init__.py)
                migration_files = list(migrations_dir.glob("*.py"))
                if len(migration_files) > 1:  # More than just __init__.py
                    app_name = f"botbalance.{app_dir.name}"
                    apps_with_migrations.append(app_name)

    return apps_with_migrations


def test_django_settings(settings_module: str) -> bool:
    """Тестирует что Django может загрузить настройки и все модели."""
    try:
        import os

        import django

        # Set settings module
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
        django.setup()

        # Try to import all models
        from django.apps import apps

        apps.check_models_ready()

        return True
    except Exception as e:
        print(f"❌ Django setup failed for {settings_module}: {e}")
        return False


def main():
    """Основная функция проверки."""
    print("🔍 Django Apps Consistency Checker")
    print("=" * 40)

    settings_dir = Path(__file__).parent / "botbalance" / "settings"
    base_py = settings_dir / "base.py"
    migrate_py = settings_dir / "migrate.py"

    # 1. Extract INSTALLED_APPS from settings files
    print("📋 Extracting INSTALLED_APPS...")
    base_apps = extract_installed_apps(base_py)
    migrate_apps = extract_installed_apps(migrate_py)

    print(f"  base.py: {len(base_apps)} apps")
    print(f"  migrate.py: {len(migrate_apps)} apps")

    # 2. Find apps with models and migrations
    print("\n🔍 Scanning for Django apps...")
    apps_with_models = find_apps_with_models()
    apps_with_migrations = find_apps_with_migrations()

    print(f"  Apps with models: {apps_with_models}")
    print(f"  Apps with migrations: {apps_with_migrations}")

    # 3. Check consistency
    print("\n⚖️ Checking consistency...")
    issues_found = False

    # Check if all apps with models are in migrate.py
    for app in apps_with_models:
        if app not in migrate_apps:
            print(f"❌ CRITICAL: {app} has models but missing from migrate.py")
            issues_found = True
        else:
            print(f"✅ {app} correctly included in migrate.py")

    # Check if all apps with migrations are in migrate.py
    for app in apps_with_migrations:
        if app not in migrate_apps:
            print(f"❌ CRITICAL: {app} has migrations but missing from migrate.py")
            issues_found = True

    # 4. Test Django settings loading
    print("\n🧪 Testing Django settings...")
    migrate_ok = test_django_settings("botbalance.settings.migrate")
    if migrate_ok:
        print("✅ migrate.py settings load successfully")
    else:
        print("❌ CRITICAL: migrate.py settings failed to load")
        issues_found = True

    # 5. Compare base.py and migrate.py apps
    print("\n🔄 Comparing settings files...")
    base_local_apps = [app for app in base_apps if app.startswith("botbalance.")]
    migrate_local_apps = [app for app in migrate_apps if app.startswith("botbalance.")]

    missing_in_migrate = set(base_local_apps) - set(migrate_local_apps)
    if missing_in_migrate:
        print(
            f"❌ CRITICAL: Apps in base.py but missing from migrate.py: {missing_in_migrate}"
        )
        issues_found = True
    else:
        print("✅ All local apps from base.py are in migrate.py")

    # 6. Final result
    print("\n" + "=" * 40)
    if issues_found:
        print("❌ FAILED: Django apps consistency issues found!")
        print("\n🔧 To fix:")
        if missing_in_migrate:
            print("   Add to migrate.py INSTALLED_APPS:")
            for app in sorted(missing_in_migrate):
                print(f'   "{app}",')
        return 1
    else:
        print("✅ SUCCESS: All Django apps are consistent!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
