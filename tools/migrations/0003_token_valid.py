# Generated by Django 4.1.4 on 2022-12-26 16:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tools', '0002_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='token',
            name='valid',
            field=models.BooleanField(default=True),
        ),
    ]
