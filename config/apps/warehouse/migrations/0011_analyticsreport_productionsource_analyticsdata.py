# Generated by Django 5.1.7 on 2025-04-10 10:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0010_remove_movement_difference_ton_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnalyticsReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_type', models.CharField(choices=[('daily', 'Ежедневный'), ('weekly', 'Еженедельный'), ('monthly', 'Ежемесячный')], max_length=10)),
                ('date_from', models.DateField()),
                ('date_to', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('file', models.FileField(blank=True, null=True, upload_to='reports/')),
            ],
            options={
                'verbose_name': 'Аналитический отчет',
                'verbose_name_plural': 'Аналитические отчеты',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProductionSource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.FloatField(verbose_name='Количество (тонны)')),
                ('percentage', models.FloatField(verbose_name='Процентное содержание (%)')),
                ('movement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='raw_materials', to='warehouse.movement')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='warehouse.product', verbose_name='Компонент')),
                ('source_reservoir', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='production_sources', to='warehouse.reservoir')),
                ('source_wagon', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='production_sources', to='warehouse.wagon')),
                ('source_warehouse', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='production_sources', to='warehouse.warehouse')),
            ],
            options={
                'verbose_name': 'Источник сырья для производства',
                'verbose_name_plural': 'Источники сырья для производства',
            },
        ),
        migrations.CreateModel(
            name='AnalyticsData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('total_received', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('total_shipped', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('total_produced', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('total_transferred', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('average_stock', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='warehouse.product')),
            ],
            options={
                'verbose_name': 'Аналитические данные',
                'verbose_name_plural': 'Аналитические данные',
                'ordering': ['-date'],
                'unique_together': {('date', 'product')},
            },
        ),
    ]
