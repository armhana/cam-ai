# Generated by Django 4.1.5 on 2023-01-22 20:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streams', '0003_stream_cam_pause'),
    ]

    operations = [
        migrations.AddField(
            model_name='stream',
            name='det_scaledown',
            field=models.IntegerField(default=0, verbose_name='scaledown'),
        ),
    ]