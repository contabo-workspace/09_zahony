import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100, verbose_name='Jmeno')),
                ('last_name', models.CharField(max_length=100, verbose_name='Prijmeni')),
                ('facebook_nickname', models.CharField(blank=True, max_length=100, verbose_name='FB prezdivka')),
                ('phone', models.CharField(max_length=30, verbose_name='Telefon')),
                ('city', models.CharField(max_length=100, verbose_name='Mesto')),
                ('note', models.TextField(blank=True, verbose_name='Poznamka')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Zakaznik',
                'verbose_name_plural': 'Zakaznici',
                'ordering': ['last_name', 'first_name'],
            },
        ),
        migrations.CreateModel(
            name='RaisedBed',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='Nazev')),
                ('dimensions', models.CharField(max_length=120, verbose_name='Rozmery')),
                ('base_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Vychozi cena')),
                ('description', models.TextField(blank=True, verbose_name='Popis')),
                ('is_active', models.BooleanField(default=True, verbose_name='Aktivni')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Zahon',
                'verbose_name_plural': 'Zahony',
                'ordering': ['name', 'dimensions'],
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ordered_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Objednano dne')),
                ('pickup_at', models.DateTimeField(verbose_name='Vyzvednuti dne a cas')),
                ('status', models.CharField(choices=[('ordered', 'Objednano'), ('in_progress', 'Pripravuje se'), ('awaiting_pickup', 'Ceka na vyzvednuti'), ('picked_up', 'Vyzvednuto'), ('cancelled', 'Zruseno')], default='ordered', max_length=20, verbose_name='Stav')),
                ('note', models.TextField(blank=True, verbose_name='Poznamka k objednavce')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='home.customer', verbose_name='Zakaznik')),
            ],
            options={
                'verbose_name': 'Objednavka',
                'verbose_name_plural': 'Objednavky',
                'ordering': ['pickup_at', 'customer__last_name'],
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='Pocet kusu')),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Cena za kus')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='home.order', verbose_name='Objednavka')),
                ('raised_bed', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='order_items', to='home.raisedbed', verbose_name='Zahon')),
            ],
            options={
                'verbose_name': 'Polozka objednavky',
                'verbose_name_plural': 'Polozky objednavky',
            },
        ),
    ]