# Generated by Django 3.0.2 on 2020-03-27 18:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calc', '0008_heir_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='heir',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
    ]
