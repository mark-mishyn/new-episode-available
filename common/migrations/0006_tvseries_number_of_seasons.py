# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-05-02 10:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0005_auto_20170502_1315'),
    ]

    operations = [
        migrations.AddField(
            model_name='tvseries',
            name='number_of_seasons',
            field=models.PositiveIntegerField(default=1),
        ),
    ]