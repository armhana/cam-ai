# Generated by Django 4.0.3 on 2022-11-16 11:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trainers', '0003_alter_trainer_wsserver'),
    ]

    operations = [
        migrations.CreateModel(
            name='client',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('hash', models.CharField(max_length=100)),
            ],
        ),
    ]