# Generated by Django 3.0.2 on 2020-03-30 18:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calc', '0011_heir_shorted_share'),
    ]

    operations = [
        migrations.AddField(
            model_name='calculation',
            name='shortage_calc',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='heir',
            name='shortage_calc',
            field=models.BooleanField(default=False),
        ),
    ]
