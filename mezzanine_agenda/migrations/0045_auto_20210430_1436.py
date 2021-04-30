# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2021-04-30 12:36
from __future__ import unicode_literals

from django.db import migrations
import mezzanine.core.fields


class Migration(migrations.Migration):

    dependencies = [
        ('mezzanine_agenda', '0044_event_streaming_comments'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='streaming_comments_en',
            field=mezzanine.core.fields.RichTextField(blank=True, null=True, verbose_name='Streaming comments'),
        ),
        migrations.AddField(
            model_name='event',
            name='streaming_comments_fr',
            field=mezzanine.core.fields.RichTextField(blank=True, null=True, verbose_name='Streaming comments'),
        ),
    ]
