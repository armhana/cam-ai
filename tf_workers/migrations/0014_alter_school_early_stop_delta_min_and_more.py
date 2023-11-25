# Generated by Django 4.2.5 on 2023-11-19 15:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tf_workers', '0013_school_model_stop_overfit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='school',
            name='early_stop_delta_min',
            field=models.FloatField(default=0.0001),
        ),
        migrations.AlterField(
            model_name='school',
            name='l_rate_delta_min',
            field=models.FloatField(default=0.0001),
        ),
    ]