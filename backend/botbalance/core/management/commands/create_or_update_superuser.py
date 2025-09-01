from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os


class Command(BaseCommand):
    help = "Create/update superuser from env DJANGO_SUPERUSER_*"

    def handle(self, *args, **opts):
        User = get_user_model()
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@botbalance.me")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "AdminPass123!")
        
        obj, created = User.objects.get_or_create(
            username=username, 
            defaults={
                "email": email, 
                "is_superuser": True, 
                "is_staff": True
            }
        )
        
        # Обновляем даже если пользователь уже существовал
        obj.email = email
        obj.is_superuser = True
        obj.is_staff = True
        obj.set_password(password)
        obj.save()
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"SUPERUSER_CREATED: {username}")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"SUPERUSER_UPDATED: {username}")
            )
        
        self.stdout.write(self.style.SUCCESS("SUPERUSER_READY"))
