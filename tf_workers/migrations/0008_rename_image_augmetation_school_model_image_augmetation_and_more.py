# Generated by Django 4.2.5 on 2023-11-09 13:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tf_workers', '0007_school_early_stop_patience_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='school',
            old_name='image_augmetation',
            new_name='model_image_augmetation',
        ),
        migrations.AddField(
            model_name='school',
            name='model_dropout',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='school',
            name='model_weight_constraint',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='school',
            name='model_weight_decay',
            field=models.FloatField(default=0.01),
        ),
    ]