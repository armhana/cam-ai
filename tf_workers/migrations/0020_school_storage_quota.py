# Generated by Django 4.2.5 on 2024-07-30 13:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tf_workers', '0019_alter_worker_timeout'),
    ]

    operations = [
        migrations.AddField(
            model_name='school',
            name='storage_quota',
            field=models.BigIntegerField(default=0),
        ),
    ]
