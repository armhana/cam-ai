# Generated by Django 4.2.5 on 2024-07-20 18:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tf_workers', '0018_alter_school_early_stop_patience_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='worker',
            name='timeout',
            field=models.FloatField(default=1.0),
        ),
    ]