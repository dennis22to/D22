# Generated by Django 2.1.1 on 2018-09-15 18:24

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('districts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='League',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('abbreviation', models.TextField()),
                ('bhv_id', models.IntegerField(unique=True)),
                ('district', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='districts.District')),
            ],
        ),
        migrations.CreateModel(
            name='Season',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_year', models.PositiveIntegerField(unique=True, validators=[django.core.validators.MinValueValidator(1990), django.core.validators.MaxValueValidator(2050)])),
            ],
        ),
        migrations.AddField(
            model_name='league',
            name='season',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='leagues.Season'),
        ),
        migrations.AlterUniqueTogether(
            name='league',
            unique_together={('abbreviation', 'district'), ('name', 'district')},
        ),
    ]
