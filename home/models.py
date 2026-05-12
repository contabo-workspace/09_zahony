from decimal import Decimal

from django.db import models
from django.utils import timezone


class Customer(models.Model):
    first_name = models.CharField('Jméno', max_length=100)
    last_name = models.CharField('Příjmení', max_length=100, blank=True)
    facebook_nickname = models.CharField('FB přezdívka', max_length=100, blank=True)
    phone = models.CharField('Telefon', max_length=30, blank=True)
    city = models.CharField('Město', max_length=100, blank=True)
    note = models.TextField('Poznámka', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Zákazník'
        verbose_name_plural = 'Zákazníci'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.last_name} {self.first_name}'

    @property
    def display_name(self):
        return f'{self.first_name} {self.last_name}'


class RaisedBed(models.Model):
    name = models.CharField('Název', max_length=120)
    dimensions = models.CharField('Rozměry', max_length=120)
    base_price = models.DecimalField('Výchozí cena', max_digits=10, decimal_places=2)
    description = models.TextField('Popis', blank=True)
    is_active = models.BooleanField('Aktivní', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Záhon'
        verbose_name_plural = 'Záhony'
        ordering = ['name', 'dimensions']

    def __str__(self):
        return f'{self.name} ({self.dimensions})'


class Order(models.Model):
    class Status(models.TextChoices):
        ASKED = 'asked', 'Poptáno'
        ORDERED = 'ordered', 'Objednáno'
        IN_PROGRESS = 'in_progress', 'Připravuje se'
        AWAITING_PICKUP = 'awaiting_pickup', 'Čeká na vyzvednutí'
        PICKED_UP = 'picked_up', 'Vyzvednuto'
        CANCELLED = 'cancelled', 'Zrušeno'

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='orders', verbose_name='Zákazník')
    ordered_at = models.DateTimeField('Objednáno dne', default=timezone.now)
    pickup_date = models.DateField('Datum vyzvednutí', blank=True, null=True)
    pickup_time = models.TimeField('Čas vyzvednutí', blank=True, null=True)
    picked_up_at = models.DateTimeField('Skutečně vyzvednuto', blank=True, null=True)
    status = models.CharField('Stav', max_length=20, choices=Status.choices, default=Status.ORDERED)
    note = models.TextField('Poznámka k objednávce', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Objednávka'
        verbose_name_plural = 'Objednávky'
        ordering = ['pickup_date', 'pickup_time', 'customer__last_name']

    def __str__(self):
        return f'Objednávka #{self.pk} - {self.customer}'

    @property
    def total_price(self):
        return sum((item.line_total for item in self.items.all()), Decimal('0.00'))

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def has_pickup_schedule(self):
        return self.pickup_date is not None

    def mark_picked_up(self, when=None):
        pickup_moment = timezone.localtime(when or timezone.now())
        self.status = self.Status.PICKED_UP
        self.picked_up_at = pickup_moment
        if self.pickup_date is None:
            self.pickup_date = pickup_moment.date()
            self.pickup_time = pickup_moment.time().replace(second=0, microsecond=0)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Objednávka')
    raised_bed = models.ForeignKey(RaisedBed, on_delete=models.PROTECT, related_name='order_items', verbose_name='Záhon')
    quantity = models.PositiveIntegerField('Počet kusů', default=1)
    unit_price = models.DecimalField('Cena za kus', max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Položka objednávky'
        verbose_name_plural = 'Položky objednávky'

    def __str__(self):
        return f'{self.raised_bed} x {self.quantity}'

    @property
    def line_total(self):
        return self.unit_price * self.quantity