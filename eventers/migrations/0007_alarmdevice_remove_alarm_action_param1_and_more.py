# Generated by Django 4.2.5 on 2024-01-04 16:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('streams', '0004_alter_stream_eve_alarm_email'),
        ('eventers', '0006_alarmdevice_remove_alarm_action_param1_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='alarm',
            name='mystream',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='streams.stream'),
        ),
    ]
