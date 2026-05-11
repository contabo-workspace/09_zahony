import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='customer',
            options={'ordering': ['last_name', 'first_name'], 'verbose_name': 'Zákazník', 'verbose_name_plural': 'Zákazníci'},
        ),
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ['pickup_at', 'customer__last_name'], 'verbose_name': 'Objednávka', 'verbose_name_plural': 'Objednávky'},
        ),
        migrations.AlterModelOptions(
            name='orderitem',
            options={'verbose_name': 'Položka objednávky', 'verbose_name_plural': 'Položky objednávky'},
        ),
        migrations.AlterModelOptions(
            name='raisedbed',
            options={'ordering': ['name', 'dimensions'], 'verbose_name': 'Záhon', 'verbose_name_plural': 'Záhony'},
        ),
        migrations.AlterField(
            model_name='customer',
            name='city',
            field=models.CharField(max_length=100, verbose_name='Město'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='facebook_nickname',
            field=models.CharField(blank=True, max_length=100, verbose_name='FB přezdívka'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='first_name',
            field=models.CharField(max_length=100, verbose_name='Jméno'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='last_name',
            field=models.CharField(max_length=100, verbose_name='Příjmení'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='note',
            field=models.TextField(blank=True, verbose_name='Poznámka'),
        ),
        migrations.AlterField(
            model_name='order',
            name='customer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='home.customer', verbose_name='Zákazník'),
        ),
        migrations.AlterField(
            model_name='order',
            name='note',
            field=models.TextField(blank=True, verbose_name='Poznámka k objednávce'),
        ),
        migrations.AlterField(
            model_name='order',
            name='ordered_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Objednáno dne'),
        ),
        migrations.AlterField(
            model_name='order',
            name='pickup_at',
            field=models.DateTimeField(verbose_name='Vyzvednutí dne a čas'),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('ordered', 'Objednáno'), ('in_progress', 'Připravuje se'), ('awaiting_pickup', 'Čeká na vyzvednutí'), ('picked_up', 'Vyzvednuto'), ('cancelled', 'Zrušeno')], default='ordered', max_length=20, verbose_name='Stav'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='home.order', verbose_name='Objednávka'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='quantity',
            field=models.PositiveIntegerField(default=1, verbose_name='Počet kusů'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='raised_bed',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='order_items', to='home.raisedbed', verbose_name='Záhon'),
        ),
        migrations.AlterField(
            model_name='raisedbed',
            name='base_price',
            field=models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Výchozí cena'),
        ),
        migrations.AlterField(
            model_name='raisedbed',
            name='dimensions',
            field=models.CharField(max_length=120, verbose_name='Rozměry'),
        ),
        migrations.AlterField(
            model_name='raisedbed',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Aktivní'),
        ),
        migrations.AlterField(
            model_name='raisedbed',
            name='name',
            field=models.CharField(max_length=120, verbose_name='Název'),
        ),
    ]