# Generated by Django 4.2.5 on 2024-07-30 13:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_alter_userinfo_allowed_schools_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinfo',
            name='storage_quota',
            field=models.BigIntegerField(default=1000000000),
        ),
    ]
