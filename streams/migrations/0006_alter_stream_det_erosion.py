# Generated by Django 4.2.5 on 2024-02-17 13:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streams', '0005_stream_det_gpu_nr_cv_stream_eve_gpu_nr_cv'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stream',
            name='det_erosion',
            field=models.IntegerField(default=1, verbose_name='erosion'),
        ),
    ]
