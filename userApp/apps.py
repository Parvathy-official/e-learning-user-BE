from django.apps import AppConfig
from django.db.models.signals import post_migrate


def auto_seed_admin(sender, **kwargs):
    try:
        from userApp.models import User
        admin_user, created = User.objects.get_or_create(
            email='admin@learnflow.com',
            defaults={
                'name': 'Master Admin',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        if created or not admin_user.check_password('admin123') or not admin_user.is_staff:
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.is_active = True
            admin_user.set_password('admin123')
            admin_user.save()
    except Exception:
        pass


class UserappConfig(AppConfig):
    name = 'userApp'

    def ready(self):
        post_migrate.connect(auto_seed_admin, sender=self)
