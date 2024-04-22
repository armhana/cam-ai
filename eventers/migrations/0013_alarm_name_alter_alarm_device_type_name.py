# Generated by Django 4.2.5 on 2024-04-22 13:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventers', '0012_alarm_mydevice'),
    ]

    operations = [
        migrations.AddField(
            model_name='alarm',
            name='name',
            field=models.CharField(default='New alarm', max_length=50),
        ),
        migrations.AlterField(
            model_name='alarm_device_type',
            name='name',
            field=models.CharField(default='New device type', max_length=50),
        ),
    ]
