# Generated by Django 4.0.3 on 2022-11-16 11:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tf_workers', '0003_alter_school_weight_boost_alter_worker_wsserver'),
    ]

    operations = [
        migrations.AddField(
            model_name='worker',
            name='wsadminpass',
            field=models.CharField(default='', max_length=50),
        ),
    ]