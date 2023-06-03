# Generated by Django 4.2.1 on 2023-06-03 10:09

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('streams', '0005_alter_stream_det_erosion'),
    ]

    operations = [
        migrations.AddField(
            model_name='stream',
            name='creator',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.SET_DEFAULT, to=settings.AUTH_USER_MODEL),
        ),
    ]
