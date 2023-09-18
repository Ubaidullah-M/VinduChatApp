# Generated by Django 4.2 on 2023-09-18 00:12

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('VinduChatApp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='sender',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sender_atm', to=settings.AUTH_USER_MODEL),
        ),
    ]