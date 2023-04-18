# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-01-07 16:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mezzanine_agenda', '0041_auto_20191106_1647'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventlocation',
            name='mappable_location',
            field=models.CharField(blank=True, help_text='This address will be used to calculate latitude and longitude. Leave blank and set Latitude and Longitude to specify the location yourself, or leave all three blank to auto-fill from the Location field.', max_length=1024),
        ),
    ]
