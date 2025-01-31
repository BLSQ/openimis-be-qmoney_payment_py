# Generated by Django 3.2.24 on 2024-04-12 09:30

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('contribution', '0003_alter_premium_options'),
        ('qmoney_payment', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Premium',
            fields=[
                ('id', models.AutoField(db_column='PremiumId', primary_key=True, serialize=False)),
                ('uuid', models.CharField(db_column='PremiumUUID', default=uuid.uuid4, max_length=36, unique=True)),
                ('amount', models.DecimalField(db_column='Amount', decimal_places=2, max_digits=18)),
                ('receipt', models.CharField(db_column='Receipt', max_length=50)),
                ('pay_type', models.CharField(db_column='PayType', max_length=1)),
                ('pay_date', models.DateField(db_column='PayDate')),
                ('is_offline', models.BooleanField(blank=True, db_column='isOffline', default=False, null=True)),
            ],
            options={
                'db_table': 'tblPremium',
                'managed': False,
            },
        ),
        migrations.RemoveField(
            model_name='qmoneypayment',
            name='contribution_uuid',
        ),
        migrations.AddField(
            model_name='qmoneypayment',
            name='premium',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contribution.premium'),
        ),
    ]
