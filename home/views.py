import calendar
from datetime import date

from django.contrib import messages
from django.db.models import Count, F, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .forms import CustomerForm, OrderForm, OrderItemForm, OrderItemFormSet, RaisedBedForm
from .models import Customer, Order, OrderItem, RaisedBed


class HomePageView(TemplateView):
    template_name = 'home/index.html'
    timeline_start_hour = 7
    timeline_end_hour = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        year = self._parse_int(self.request.GET.get('year'), today.year)
        month = self._parse_int(self.request.GET.get('month'), today.month)
        month = min(max(month, 1), 12)

        current_month = date(year, month, 1)
        cal = calendar.Calendar(firstweekday=0)

        scheduled_orders = (
            Order.objects.select_related('customer')
            .prefetch_related(Prefetch('items', queryset=OrderItem.objects.select_related('raised_bed')))
            .filter(pickup_at__year=year, pickup_at__month=month)
            .order_by('pickup_at', 'customer__last_name')
        )

        entries_by_day_hour = {}
        for order in scheduled_orders:
            pickup_local = timezone.localtime(order.pickup_at)
            order_day = pickup_local.date()
            slot_hour = self._slot_hour(pickup_local.hour)
            entries_by_day_hour.setdefault((order_day, slot_hour), []).append(
                self._build_scheduled_order(order, pickup_local)
            )

        undated_orders = list(
            Order.objects.select_related('customer')
            .prefetch_related(Prefetch('items', queryset=OrderItem.objects.select_related('raised_bed')))
            .filter(ordered_at__year=year, ordered_at__month=month, pickup_at__isnull=True)
            .exclude(status__in=[Order.Status.PICKED_UP, Order.Status.CANCELLED])
            .order_by('ordered_at', 'customer__last_name')
        )
        for order in undated_orders:
            ordered_local = timezone.localtime(order.ordered_at)
            ordered_day = ordered_local.date()
            slot_hour = self._slot_hour(ordered_local.hour)
            entries_by_day_hour.setdefault((ordered_day, slot_hour), []).append(
                self._build_unscheduled_order(order, ordered_local)
            )

        time_slots = [
            {
                'hour': hour,
                'label': f'{hour}:00',
            }
            for hour in range(self.timeline_start_hour, self.timeline_end_hour + 1)
        ]

        slot_max_entries = {slot['hour']: 0 for slot in time_slots}
        month_days = []
        for day_number in range(1, calendar.monthrange(year, month)[1] + 1):
            row_date = date(year, month, day_number)
            hourly_cells = []
            has_entries = False
            for slot in time_slots:
                slot_entries = entries_by_day_hour.get((row_date, slot['hour']), [])
                slot_entries = sorted(slot_entries, key=lambda item: item['sort_time'])
                if slot_entries:
                    has_entries = True
                    slot_max_entries[slot['hour']] = max(slot_max_entries[slot['hour']], len(slot_entries))
                hourly_cells.append(
                    {
                        'hour': slot['hour'],
                        'entries': slot_entries,
                    }
                )

            month_days.append(
                {
                    'date': row_date,
                    'weekday_label': self._weekday_label(row_date),
                    'is_today': row_date == today,
                    'hourly_cells': hourly_cells,
                    'has_content': has_entries,
                }
            )

        for slot in time_slots:
            max_entries = slot_max_entries[slot['hour']]
            slot['has_entries'] = max_entries > 0
            slot['width_rem'] = 3.4 if max_entries == 0 else min(7.8 * max_entries, 28)

        previous_month = self._shift_month(current_month, -1)
        next_month = self._shift_month(current_month, 1)
        global_status_counts = self._status_counts(Order.objects.all())

        context.update(
            {
                'calendar_days': month_days,
                'current_month': current_month,
                'previous_month': previous_month,
                'next_month': next_month,
                'time_slots': time_slots,
                'overview_metrics': [
                    {
                        'label': 'K vyřízení',
                        'count': self._open_count(global_status_counts),
                    },
                    {
                        'label': 'Poptáno',
                        'count': global_status_counts.get(Order.Status.ASKED, 0),
                    },
                    {
                        'label': 'Objednáno',
                        'count': global_status_counts.get(Order.Status.ORDERED, 0),
                    },
                ],
            }
        )
        return context

    def _build_scheduled_order(self, order, pickup_local):
        return {
            'id': order.id,
            'facebook_nickname': order.customer.facebook_nickname or order.customer.display_name,
            'customer_name': order.customer.display_name,
            'meta_time': pickup_local.strftime('%H:%M'),
            'meta_label': 'Vyzvednutí',
            'status': order.get_status_display(),
            'status_code': order.status,
            'item_count': self._item_count(order),
            'total_price': self._price_label(order),
            'sort_time': pickup_local.time(),
        }

    def _build_unscheduled_order(self, order, ordered_local):
        return {
            'id': order.id,
            'facebook_nickname': order.customer.facebook_nickname or order.customer.display_name,
            'customer_name': order.customer.display_name,
            'meta_time': ordered_local.strftime('%H:%M'),
            'meta_label': order.get_status_display(),
            'status': order.get_status_display(),
            'status_code': order.status,
            'item_count': self._item_count(order),
            'total_price': self._price_label(order),
            'sort_time': ordered_local.time(),
        }

    def _item_count(self, order):
        return sum(item.quantity for item in order.items.all())

    def _price_label(self, order):
        return f"{order.total_price:,.0f} Kč".replace(',', ' ')

    def _slot_hour(self, hour):
        return min(max(hour, self.timeline_start_hour), self.timeline_end_hour)

    def _weekday_label(self, value):
        return ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne'][value.weekday()]

    def _parse_int(self, value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _shift_month(self, value, offset):
        month_index = (value.month - 1) + offset
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        return date(year, month, 1)

    def _build_status_summary(self, orders):
        counts = {status: 0 for status, _label in Order.Status.choices}
        for order in orders:
            counts[order.status] += 1
        return [
            {
                'code': status,
                'label': label,
                'count': counts[status],
            }
            for status, label in Order.Status.choices
        ]

    def _status_counts(self, queryset):
        return {
            item['status']: item['count']
            for item in queryset.values('status').annotate(count=Count('id'))
        }

    def _open_count(self, status_counts):
        open_statuses = [
            Order.Status.ASKED,
            Order.Status.ORDERED,
            Order.Status.IN_PROGRESS,
            Order.Status.AWAITING_PICKUP,
        ]
        return sum(status_counts.get(status, 0) for status in open_statuses)


class OrderListView(TemplateView):
    template_name = 'home/order_list.html'

    SORT_OPTIONS = [
        ('pickup_asc', 'Nejbližší vyzvednutí'),
        ('pickup_desc', 'Nejpozdější vyzvednutí'),
        ('ordered_desc', 'Nejnovější objednávky'),
        ('ordered_asc', 'Nejstarší objednávky'),
        ('customer_asc', 'Zákazník A-Z'),
        ('status_asc', 'Stav'),
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get('q', '').strip()
        selected_status = self.request.GET.get('status', '').strip()
        selected_city = self.request.GET.get('city', '').strip()
        selected_sort = self.request.GET.get('sort', 'pickup_asc').strip() or 'pickup_asc'

        queryset = (
            Order.objects.select_related('customer')
            .prefetch_related(Prefetch('items', queryset=OrderItem.objects.select_related('raised_bed')))
        )

        if search_query:
            queryset = queryset.filter(
                Q(customer__first_name__icontains=search_query)
                | Q(customer__last_name__icontains=search_query)
                | Q(customer__facebook_nickname__icontains=search_query)
                | Q(customer__phone__icontains=search_query)
                | Q(customer__city__icontains=search_query)
                | Q(note__icontains=search_query)
                | Q(items__raised_bed__name__icontains=search_query)
                | Q(items__raised_bed__dimensions__icontains=search_query)
            ).distinct()

        valid_statuses = {status for status, _label in Order.Status.choices}
        if selected_status in valid_statuses:
            queryset = queryset.filter(status=selected_status)

        if selected_city:
            queryset = queryset.filter(customer__city=selected_city)

        queryset = self._apply_sort(queryset, selected_sort)
        orders = list(queryset)

        context.update(
            {
                'orders': orders,
                'status_summary': self._build_filtered_status_summary(orders),
                'sort_options': self.SORT_OPTIONS,
                'status_options': Order.Status.choices,
                'city_options': self._city_options(),
                'selected_status': selected_status,
                'selected_city': selected_city,
                'selected_sort': selected_sort,
                'search_query': search_query,
                'total_orders': len(orders),
                'orders_with_pickup': sum(1 for order in orders if order.pickup_at),
                'orders_without_pickup': sum(1 for order in orders if not order.pickup_at),
                'open_orders': sum(
                    1
                    for order in orders
                    if order.status in {
                        Order.Status.ASKED,
                        Order.Status.ORDERED,
                        Order.Status.IN_PROGRESS,
                        Order.Status.AWAITING_PICKUP,
                    }
                ),
            }
        )
        return context

    def _city_options(self):
        return list(
            Customer.objects.exclude(city='')
            .order_by('city')
            .values_list('city', flat=True)
            .distinct()
        )

    def _apply_sort(self, queryset, selected_sort):
        sort_map = {
            'pickup_asc': [F('pickup_at').asc(nulls_last=True), 'customer__last_name', 'customer__first_name'],
            'pickup_desc': [F('pickup_at').desc(nulls_last=True), 'customer__last_name', 'customer__first_name'],
            'ordered_desc': ['-ordered_at', 'customer__last_name', 'customer__first_name'],
            'ordered_asc': ['ordered_at', 'customer__last_name', 'customer__first_name'],
            'customer_asc': ['customer__last_name', 'customer__first_name', F('pickup_at').asc(nulls_last=True)],
            'status_asc': ['status', F('pickup_at').asc(nulls_last=True), 'customer__last_name'],
        }
        return queryset.order_by(*sort_map.get(selected_sort, sort_map['pickup_asc']))

    def _build_filtered_status_summary(self, orders):
        counts = {status: 0 for status, _label in Order.Status.choices}
        for order in orders:
            counts[order.status] += 1
        return [
            {
                'code': status,
                'label': label,
                'count': counts[status],
            }
            for status, label in Order.Status.choices
        ]


class OrderCreateView(TemplateView):
    template_name = 'home/order_form.html'

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        order_form = OrderForm(request.POST)
        item_formset = OrderItemFormSet(request.POST, prefix='items')

        if order_form.is_valid() and item_formset.is_valid():
            order = order_form.save()
            item_formset.instance = order
            item_formset.save()
            messages.success(request, 'Objednávka byla uložena.')
            return redirect('home:index')

        return self.render_to_response(
            self.get_context_data(order_form=order_form, item_formset=item_formset)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_form = kwargs.get('order_form') or OrderForm()
        item_formset = kwargs.get('item_formset') or OrderItemFormSet(prefix='items')

        selected_customer_label = ''
        customer_value = order_form['customer'].value()
        if customer_value:
            selected_customer_label = self._get_customer_label(customer_value)

        selected_status_label = ''
        status_value = order_form['status'].value()
        if status_value:
            selected_status_label = dict(Order.Status.choices).get(status_value, '')

        pickup_value = order_form['pickup_at'].value() or ''
        pickup_display = str(pickup_value).replace('T', ' ') if pickup_value else ''

        context.update(
            {
                'order_form': order_form,
                'item_formset': item_formset,
                'item_modal_form': OrderItemForm(prefix='item_modal'),
                'customer_form': CustomerForm(prefix='customer_modal'),
                'raised_bed_form': RaisedBedForm(prefix='raised_bed_modal'),
                'beds_payload': self._beds_payload(),
                'item_rows': self._build_item_rows(item_formset),
                'selected_customer_label': selected_customer_label,
                'selected_status_label': selected_status_label,
                'selected_pickup_display': pickup_display,
                'summary_total': self._calculate_summary_total(item_formset),
            }
        )
        return context

    def _beds_payload(self):
        return [
            {
                'id': bed.id,
                'label': str(bed),
                'base_price': str(bed.base_price),
            }
            for bed in RaisedBed.objects.filter(is_active=True).order_by('name', 'dimensions')
        ]

    def _get_customer_label(self, customer_id):
        try:
            customer = Customer.objects.get(pk=customer_id)
        except (Customer.DoesNotExist, ValueError, TypeError):
            return ''
        return customer.display_name

    def _build_item_rows(self, item_formset):
        rows = []
        bed_lookup = {str(bed.id): str(bed) for bed in RaisedBed.objects.all()}
        for index, form in enumerate(item_formset.forms):
            bed_value = form['raised_bed'].value()
            rows.append(
                {
                    'index': index,
                    'bed_label': bed_lookup.get(str(bed_value), 'Záhon není vybraný'),
                    'quantity': form['quantity'].value() or 0,
                    'unit_price': form['unit_price'].value() or '0,00',
                    'delete_checked': bool(form['DELETE'].value()),
                }
            )
        return rows

    def _calculate_summary_total(self, item_formset):
        total = 0
        for form in item_formset.forms:
            if form['DELETE'].value():
                continue
            quantity = form['quantity'].value() or 0
            unit_price = form['unit_price'].value() or 0
            try:
                total += float(quantity) * float(str(unit_price).replace(',', '.'))
            except (TypeError, ValueError):
                continue
        return f'{total:.2f}'.replace('.', ',')


class CustomerModalCreateView(View):
    def post(self, request, *args, **kwargs):
        form = CustomerForm(request.POST, prefix='customer_modal')
        if form.is_valid():
            customer = form.save()
            return JsonResponse(
                {
                    'customer': {
                        'id': customer.id,
                        'label': customer.display_name,
                    }
                }
            )
        return JsonResponse({'errors': self._flatten_errors(form)}, status=400)

    def _flatten_errors(self, form):
        errors = []
        for field_name, field_errors in form.errors.items():
            label = form.fields.get(field_name).label if field_name in form.fields else ''
            for error in field_errors:
                errors.append(f'{label}: {error}' if label else error)
        return errors


class RaisedBedModalCreateView(View):
    def post(self, request, *args, **kwargs):
        form = RaisedBedForm(request.POST, prefix='raised_bed_modal')
        if form.is_valid():
            raised_bed = form.save()
            return JsonResponse(
                {
                    'raised_bed': {
                        'id': raised_bed.id,
                        'label': str(raised_bed),
                        'base_price': str(raised_bed.base_price),
                    }
                }
            )
        return JsonResponse({'errors': self._flatten_errors(form)}, status=400)

    def _flatten_errors(self, form):
        errors = []
        for field_name, field_errors in form.errors.items():
            label = form.fields.get(field_name).label if field_name in form.fields else ''
            for error in field_errors:
                errors.append(f'{label}: {error}' if label else error)
        return errors
