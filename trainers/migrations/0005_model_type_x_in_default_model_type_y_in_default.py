# Generated by Django 4.2.5 on 2023-11-13 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trainers', '0004_fit_early_stop_delta_min_fit_early_stop_patience_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='model_type',
            name='x_in_default',
            field=models.IntegerField(default=224),
        ),
        migrations.AddField(
            model_name='model_type',
            name='y_in_default',
            field=models.IntegerField(default=224),
        ),
    ]
