# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2019-06-19 17:58
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mezzanine_agenda', '0032_auto_20190619_1951'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='event',
            options={'ordering': ('rank', 'start'), 'permissions': (('user_edit', 'Mezzo - User can edit its own content'), ('user_delete', 'Mezzo - User can delete its own content'), ('team_edit', "Mezzo - User can edit his team's content"), ('team_delete', "Mezzo - User can delete his team's content")), 'verbose_name': 'Event', 'verbose_name_plural': 'Events'},
        ),
    ]
