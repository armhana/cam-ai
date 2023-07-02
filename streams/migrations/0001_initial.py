# Generated by Django 4.0.3 on 2022-11-04 18:55

from django.db import migrations, models
from django.conf import settings
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

  initial = True

  dependencies = [
      ('tf_workers', '0001_initial'),
  ]

  operations = [
    migrations.CreateModel(
      name='stream',
      fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('active', models.BooleanField(default=True)),
        ('name', models.CharField(default='New Stream', max_length=100)),
        ('made', models.DateTimeField(default=django.utils.timezone.now)),
        ('lastused', models.DateTimeField(default=django.utils.timezone.now)),
        ('creator', models.ForeignKey(default=1, on_delete=django.db.models.deletion.SET_DEFAULT, to=settings.AUTH_USER_MODEL)),
        ('cam_mode_flag', models.IntegerField(default=2)),
        ('cam_view', models.BooleanField(default=True)),
        ('cam_xres', models.IntegerField(default=0)),
        ('cam_yres', models.IntegerField(default=0)),
        ('cam_fpslimit', models.FloatField(default=2, verbose_name='FPS limit')),
        ('cam_fpsactual', models.FloatField(default=0)),
        ('cam_feed_type', models.IntegerField(choices=[(1, 'JPeg'), (2, 'Others'), (3, 'RTSP')], default=2, verbose_name='feed type')),
        ('cam_url', models.CharField(default='rtmp://192.168.1.99/bcs/channel0_main.bcs?channel=0&stream=1&user=user1&password=password1', max_length=256, verbose_name='video url')),
        ('cam_apply_mask', models.BooleanField(default=False)),
        ('cam_repeater', models.IntegerField(default=0)),
        ('cam_checkdoubles', models.BooleanField(default=True)),
        ('cam_latency', models.FloatField(default=60.0)),
        ('cam_ffmpeg_fps', models.FloatField(default=0, verbose_name='ffmpeg FPS limit')),
        ('cam_ffmpeg_segment', models.FloatField(default=10, verbose_name='ffmpeg segment length')),
        ('cam_ffmpeg_crf', models.IntegerField(default=23, verbose_name='ffmpeg CRF')),
        ('cam_video_codec', models.IntegerField(default=-1)),
        ('cam_audio_codec', models.IntegerField(default=-1)),
        ('cam_max_x_view', models.IntegerField(default=0)),
        ('cam_min_x_view', models.IntegerField(default=0)),
        ('cam_scale_x_view', models.FloatField(default=1.0)),
        ('cam_pause', models.BooleanField(default=False)),
        ('det_mode_flag', models.IntegerField(default=2)),
        ('det_view', models.BooleanField(default=True)),
        ('det_fpslimit', models.FloatField(default=0, verbose_name='FPS limit')),
        ('det_fpsactual', models.FloatField(default=0)),
        ('det_threshold', models.IntegerField(default=40, verbose_name='threshold')),
        ('det_backgr_delay', models.IntegerField(default=1, verbose_name='background delay')),
        ('det_dilation', models.IntegerField(default=20, verbose_name='dilation')),
        ('det_erosion', models.IntegerField(default=3, verbose_name='erosion')),
        ('det_max_rect', models.IntegerField(default=20, verbose_name='max. number')),
        ('det_max_size', models.IntegerField(default=100, verbose_name='max. size')),
        ('det_apply_mask', models.BooleanField(default=False)),
        ('det_max_x_view', models.IntegerField(default=0)),
        ('det_min_x_view', models.IntegerField(default=0)),
        ('det_scale_x_view', models.FloatField(default=1.0)),
        ('det_scaledown', models.IntegerField(default=0, verbose_name='scaledown')),
        ('eve_mode_flag', models.IntegerField(default=2)),
        ('eve_view', models.BooleanField(default=True)),
        ('eve_fpslimit', models.FloatField(default=0, verbose_name='FPS limit')),
        ('eve_fpsactual', models.FloatField(default=0)),
        ('eve_alarm_email', models.CharField(default='theo@tester123.de', max_length=255, verbose_name='alarm email')),
        ('eve_event_time_gap', models.IntegerField(default=60, verbose_name='new event gap')),
        ('eve_margin', models.IntegerField(default=20, verbose_name='frame margin')),
        ('eve_all_predictions', models.BooleanField(default=True)),
        ('eve_school', models.ForeignKey(default=1, on_delete=django.db.models.deletion.SET_DEFAULT, to='tf_workers.school')),
        ('eve_max_x_view', models.IntegerField(default=0)),
        ('eve_min_x_view', models.IntegerField(default=0)),
        ('eve_scale_x_view', models.FloatField(default=1.0)),
      ],
    ),
  ]
