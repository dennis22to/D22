# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-03-18 14:59
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0014_auto_20180313_0100'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='forfeiting_team',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='forfeiting_team', to='base.Team'),
        ),
    ]