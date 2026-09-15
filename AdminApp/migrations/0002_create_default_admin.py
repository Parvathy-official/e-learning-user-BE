from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_or_update_admin(apps, schema_editor):
    User = apps.get_model('userApp', 'User')
    admin_user = User.objects.filter(email='admin@learnflow.com').first()
    if not admin_user:
        admin_user = User.objects.create(
            email='admin@learnflow.com',
            name='Master Admin',
            is_staff=True,
            is_superuser=True,
            is_active=True,
            password=make_password('admin123'),
        )
    else:
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.is_active = True
        admin_user.password = make_password('admin123')
        admin_user.save()


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('AdminApp', '0001_initial'),
        ('userApp', '0003_razorpaywebhookevent'),
    ]

    operations = [
        migrations.RunPython(create_or_update_admin, reverse_func),
    ]
