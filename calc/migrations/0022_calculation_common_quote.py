# Generated by Django 3.0.5 on 2020-05-30 17:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calc', '0021_calculation_maternal_quote'),
    ]

    operations = [
        migrations.AddField(
            model_name='calculation',
            name='common_quote',
            field=models.BooleanField(default=False),
        ),
    ]
