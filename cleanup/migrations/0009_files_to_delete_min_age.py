# Generated by Django 4.2.5 on 2024-07-24 15:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cleanup', '0008_rename_video_correct_status_line_video_videos_correct_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='files_to_delete',
            name='min_age',
            field=models.FloatField(default=0.0),
        ),
    ]
