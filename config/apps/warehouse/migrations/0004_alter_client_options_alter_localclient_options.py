# Generated by Django 5.1.7 on 2025-03-25 08:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0003_remove_localmovement_mass_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='client',
            options={'verbose_name': 'Klient', 'verbose_name_plural': 'Klientlar'},
        ),
        migrations.AlterModelOptions(
            name='localclient',
            options={'verbose_name': 'Mahalliy Klient', 'verbose_name_plural': ' Mahalliy Klientlar'},
        ),
    ]
