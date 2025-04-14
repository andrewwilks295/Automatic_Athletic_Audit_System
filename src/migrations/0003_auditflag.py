# Generated by Django 5.1.5 on 2025-04-14 19:51

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('src', '0002_student_declared_major_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditFlag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=64)),
                ('level', models.CharField(choices=[('error', 'Error'), ('warning', 'Warning'), ('info', 'Info')], max_length=10)),
                ('message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('student_audit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='flags', to='src.studentaudit')),
            ],
        ),
    ]
