# Generated by Django 5.1.7 on 2025-03-28 19:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0004_alter_client_options_alter_localclient_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='Transport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transport_number', models.CharField(max_length=100)),
                ('density', models.FloatField(blank=True, null=True)),
                ('temperature', models.FloatField(default=20)),
                ('liter', models.FloatField(blank=True, null=True)),
                ('quantity', models.FloatField()),
                ('doc_ton', models.FloatField(blank=True, null=True)),
                ('movement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transports', to='warehouse.movement')),
            ],
            options={
                'verbose_name': 'Transport',
                'verbose_name_plural': 'Transports',
            },
        ),
    ]
