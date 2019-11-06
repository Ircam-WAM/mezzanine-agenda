# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2019-11-06 15:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mezzanine_agenda', '0040_externalshop_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='externalshop',
            name='title_en',
            field=models.CharField(blank=True, help_text='Used for display', max_length=512, null=True, verbose_name='title'),
        ),
        migrations.AddField(
            model_name='externalshop',
            name='title_fr',
            field=models.CharField(blank=True, help_text='Used for display', max_length=512, null=True, verbose_name='title'),
        ),
    ]
