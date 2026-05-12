from django.contrib import admin

from .models import Customer, Order, OrderItem, RaisedBed


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'facebook_nickname', 'phone', 'city')
    search_fields = ('first_name', 'last_name', 'facebook_nickname', 'phone', 'city')
    list_filter = ('city',)


@admin.register(RaisedBed)
class RaisedBedAdmin(admin.ModelAdmin):
    list_display = ('name', 'dimensions', 'base_price', 'is_active')
    search_fields = ('name', 'dimensions', 'description')
    list_filter = ('is_active',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    autocomplete_fields = ('raised_bed',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'status', 'ordered_at', 'pickup_date', 'pickup_time', 'picked_up_at', 'get_total_price')
    list_filter = ('status', 'pickup_date', 'picked_up_at', 'ordered_at')
    search_fields = (
        'customer__first_name',
        'customer__last_name',
        'customer__facebook_nickname',
        'customer__phone',
        'note',
    )
    date_hierarchy = 'pickup_date'
    autocomplete_fields = ('customer',)
    inlines = [OrderItemInline]

    def get_total_price(self, obj):
        return obj.total_price

    get_total_price.short_description = 'Celková cena'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'raised_bed', 'quantity', 'unit_price', 'line_total')
    list_select_related = ('order', 'raised_bed')
    autocomplete_fields = ('order', 'raised_bed')
    search_fields = ('order__customer__last_name', 'raised_bed__name', 'raised_bed__dimensions')