# Generated by Django 2.1.1 on 2018-09-15 18:24

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('associations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='District',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField(unique=True)),
                ('bhv_id', models.IntegerField(unique=True)),
                ('associations', models.ManyToManyField(to='associations.Association')),
            ],
        ),
    ]
