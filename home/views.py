from datetime import datetime, timedelta

from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .forms import CustomerForm, OrderForm, OrderItemForm, OrderItemFormSet, RaisedBedForm, format_czech_date
from .models import Customer, Order, OrderItem, RaisedBed


def flatten_form_errors(form):
    errors = []
    for field_name, field_errors in form.errors.items():
        label = form.fields.get(field_name).label if field_name in form.fields else ''
        for error in field_errors:
            errors.append(f'{label}: {error}' if label else error)
    return errors


def format_price_label(value):
    total_value = value.total_price if hasattr(value, 'total_price') else value
    return f"{total_value:,.0f} Kč".replace(',', ' ')


def format_datetime_label(value):
    return f"{format_czech_date(value.date())} {value.strftime('%H:%M')}"


def format_pickup_time_label(value):
    return value.strftime('%H:%M') if value else 'Čas neuveden'


def format_pickup_schedule_label(order):
    if not order.pickup_date:
        return 'Bez termínu'
    if not order.pickup_time:
        return f'{format_czech_date(order.pickup_date)} čas neuveden'
    return f'{format_czech_date(order.pickup_date)} {order.pickup_time.strftime("%H:%M")}'


class HomePageView(TemplateView):
    template_name = 'home/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        open_orders = self._open_orders_queryset()
        month_revenue = self._month_revenue(today)
        today_pickups = [
            self._build_order_card(order, card_type='pickup', today=today)
            for order in open_orders.filter(pickup_date=today).order_by('pickup_time', 'customer__last_name')
        ]
        upcoming_pickup_groups = self._build_upcoming_pickup_groups(open_orders, today)
        undated_orders = [
            self._build_order_card(order, card_type='undated', today=today)
            for order in open_orders.filter(pickup_date__isnull=True).order_by('ordered_at', 'customer__last_name')
        ]
        global_status_counts = self._status_counts(open_orders)

        context.update(
            {
                'today_label': format_czech_date(today),
                'today_pickups': today_pickups,
                'upcoming_pickup_groups': upcoming_pickup_groups,
                'undated_orders': undated_orders,
                'overview_metrics': [
                    {
                        'label': 'Dnes k vyzvednutí',
                        'count': len(today_pickups),
                    },
                    {
                        'label': 'Bez termínu',
                        'count': len(undated_orders),
                    },
                    {
                        'label': 'K vyřízení',
                        'count': self._open_count(global_status_counts),
                    },
                    {
                        'label': 'Obrat za měsíc',
                        'count': self._price_label(month_revenue),
                    },
                ],
            }
        )
        return context

    def _open_orders_queryset(self):
        return (
            Order.objects.select_related('customer')
            .prefetch_related(Prefetch('items', queryset=OrderItem.objects.select_related('raised_bed')))
            .exclude(status__in=[Order.Status.PICKED_UP, Order.Status.CANCELLED])
        )

    def _build_order_card(self, order, card_type, today=None, include_delete=False):
        ordered_local = timezone.localtime(order.ordered_at)
        primary_name = order.customer.facebook_nickname or order.customer.display_name
        secondary_name = order.customer.display_name if order.customer.facebook_nickname else ''
        card = {
            'id': order.id,
            'edit_url': reverse('home:order-modal-update', args=[order.id]),
            'picked_up_url': reverse('home:order-mark-picked-up', args=[order.id]),
            'delete_url': reverse('home:order-delete', args=[order.id]) if include_delete else '',
            'can_mark_picked_up': order.status not in [Order.Status.PICKED_UP, Order.Status.CANCELLED],
            'primary_name': primary_name,
            'secondary_name': secondary_name,
            'status': order.get_status_display(),
            'status_code': order.status,
            'item_count': order.item_count,
            'total_price': format_price_label(order),
            'items_preview': self._items_preview(order),
            'note': order.note,
            'show_delete': include_delete,
            'meta_items': [],
        }

        if card_type == 'pickup':
            card['meta_items'] = [
                {'label': 'Vyzvednutí', 'value': format_pickup_time_label(order.pickup_time)},
                {'label': 'Objednáno', 'value': format_datetime_label(ordered_local)},
            ]
            if today and order.pickup_date:
                card['pickup_day_label'] = self._pickup_group_label(order.pickup_date, today)
            return card

        if card_type == 'undated':
            card['meta_items'] = [
                {'label': 'Objednáno', 'value': format_datetime_label(ordered_local)},
                {'label': 'Vyzvednutí', 'value': 'Bez termínu'},
            ]
            return card

        card['meta_items'] = [
            {'label': 'Objednáno', 'value': format_datetime_label(ordered_local)},
            {'label': 'Vyzvednutí', 'value': format_pickup_schedule_label(order)},
        ]
        return card

    def _build_upcoming_pickup_groups(self, queryset, today):
        groups = []
        current_group = None
        for order in queryset.filter(pickup_date__gt=today).order_by('pickup_date', 'pickup_time', 'customer__last_name'):
            pickup_date = order.pickup_date
            if current_group is None or current_group['date'] != pickup_date:
                current_group = {
                    'date': pickup_date,
                    'label': self._pickup_group_label(pickup_date, today),
                    'date_display': format_czech_date(pickup_date),
                    'orders': [],
                }
                groups.append(current_group)
            current_group['orders'].append(self._build_order_card(order, card_type='pickup', today=today))
        return groups

    def _build_order_list_card(self, order):
        return self._build_order_card(order, card_type='list', include_delete=True)

    def _items_preview(self, order):
        items = list(order.items.all())
        previews = [str(item.raised_bed) for item in items[:2]]
        if not previews:
            return 'Bez položek'
        if len(items) > 2:
            previews.append(f'+{len(items) - 2} další')
        return ' • '.join(previews)

    def _month_revenue(self, today):
        monthly_orders = (
            Order.objects.prefetch_related(Prefetch('items', queryset=OrderItem.objects.select_related('raised_bed')))
            .filter(
                status=Order.Status.PICKED_UP,
                picked_up_at__year=today.year,
                picked_up_at__month=today.month,
            )
        )
        return sum((order.total_price for order in monthly_orders), start=0)

    def _pickup_group_label(self, value, today):
        if value == today:
            return 'Dnes'
        if value == today + timedelta(days=1):
            return 'Zítra'
        weekday_labels = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne']
        return f"{weekday_labels[value.weekday()]} {format_czech_date(value)}"

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


class OrderListView(HomePageView):
    template_name = 'home/order_list.html'

    def get_context_data(self, **kwargs):
        context = TemplateView.get_context_data(self, **kwargs)
        today = timezone.localdate()
        queryset = (
            Order.objects.select_related('customer')
            .prefetch_related(Prefetch('items', queryset=OrderItem.objects.select_related('raised_bed')))
            .all()
        )

        search = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', 'all')
        pickup_filter = self.request.GET.get('pickup', 'all')

        if search:
            queryset = queryset.filter(
                Q(customer__first_name__icontains=search)
                | Q(customer__last_name__icontains=search)
                | Q(customer__facebook_nickname__icontains=search)
                | Q(customer__phone__icontains=search)
                | Q(note__icontains=search)
            )

        if status_filter == 'open':
            queryset = queryset.exclude(status__in=[Order.Status.PICKED_UP, Order.Status.CANCELLED])
        elif status_filter != 'all' and status_filter in dict(Order.Status.choices):
            queryset = queryset.filter(status=status_filter)

        if pickup_filter == 'today':
            queryset = queryset.filter(pickup_date=today)
        elif pickup_filter == 'with_date':
            queryset = queryset.filter(pickup_date__isnull=False)
        elif pickup_filter == 'without_date':
            queryset = queryset.filter(pickup_date__isnull=True)
        elif pickup_filter == 'month':
            queryset = queryset.filter(pickup_date__year=today.year, pickup_date__month=today.month)
        elif pickup_filter == 'overdue':
            queryset = queryset.filter(pickup_date__lt=today).exclude(status__in=[Order.Status.PICKED_UP, Order.Status.CANCELLED])

        queryset = queryset.order_by('-updated_at', '-ordered_at')

        context.update(
            {
                'orders': [self._build_order_list_card(order) for order in queryset],
                'search_query': search,
                'selected_status': status_filter,
                'selected_pickup': pickup_filter,
                'status_options': [
                    ('all', 'Všechny stavy'),
                    ('open', 'Jen aktivní'),
                    *Order.Status.choices,
                ],
                'pickup_options': [
                    ('all', 'Všechny termíny'),
                    ('today', 'Dnes k vyzvednutí'),
                    ('with_date', 'Jen s termínem'),
                    ('without_date', 'Bez termínu'),
                    ('month', 'Termín tento měsíc'),
                    ('overdue', 'Po termínu'),
                ],
                'order_count': queryset.count(),
            }
        )
        return context


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

        pickup_date_value = order_form['pickup_date'].value() or ''
        pickup_time_value = order_form['pickup_time'].value() or ''
        formatted_pickup_date = self._format_date_value(pickup_date_value)
        if formatted_pickup_date:
            pickup_display = f'{formatted_pickup_date} {pickup_time_value}'.strip() if pickup_time_value else f'{formatted_pickup_date} čas neuveden'
        else:
            pickup_display = ''

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

    def _format_date_value(self, value):
        if not value:
            return ''
        for input_format in ['%Y-%m-%d', '%d.%m.%Y', '%d. %m. %Y']:
            try:
                parsed = datetime.strptime(str(value), input_format).date()
                return format_czech_date(parsed)
            except ValueError:
                continue
        return str(value)

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
        return JsonResponse({'errors': flatten_form_errors(form)}, status=400)


class OrderModalUpdateView(View):
    template_name = 'home/modals/order_edit_modal.html'

    def get(self, request, pk, *args, **kwargs):
        order = self._get_order(pk)
        form = OrderForm(instance=order, prefix='order_edit')
        self._apply_compact_schedule_attrs(form)
        item_formset = OrderItemFormSet(instance=order, prefix='order_items_edit')
        return render(request, self.template_name, self._get_context(order, form, item_formset))

    def post(self, request, pk, *args, **kwargs):
        order = self._get_order(pk)
        form = OrderForm(request.POST, instance=order, prefix='order_edit')
        self._apply_compact_schedule_attrs(form)
        item_formset = OrderItemFormSet(request.POST, instance=order, prefix='order_items_edit')
        if form.is_valid() and item_formset.is_valid():
            form.save()
            item_formset.save()
            return JsonResponse({'success': True, 'message': 'Objednávka byla upravena.'})
        return render(request, self.template_name, self._get_context(order, form, item_formset), status=400)

    def _get_context(self, order, form, item_formset):
        return {
            'order': order,
            'order_edit_form': form,
            'order_item_formset': item_formset,
            'order_item_modal_form': OrderItemForm(prefix='order_item_modal'),
            'order_items': order.items.select_related('raised_bed').all(),
        }

    def _get_order(self, pk):
        return get_object_or_404(
            Order.objects.select_related('customer').prefetch_related(
                Prefetch('items', queryset=OrderItem.objects.select_related('raised_bed'))
            ),
            pk=pk,
        )

    def _apply_compact_schedule_attrs(self, form):
        field_attrs = {
            'ordered_date': {'placeholder': 'Datum', 'aria-label': 'Datum objednávky'},
            'ordered_time': {'placeholder': 'Čas', 'aria-label': 'Čas objednávky'},
            'pickup_date': {'placeholder': 'Datum', 'aria-label': 'Datum vyzvednutí'},
            'pickup_time': {'placeholder': 'Čas', 'aria-label': 'Čas vyzvednutí'},
        }
        for field_name, attrs in field_attrs.items():
            form.fields[field_name].widget.attrs.update(attrs)


class OrderMarkPickedUpView(View):
    def post(self, request, pk, *args, **kwargs):
        order = get_object_or_404(Order, pk=pk)
        order.mark_picked_up()
        order.save(update_fields=['status', 'pickup_date', 'pickup_time', 'picked_up_at', 'updated_at'])
        messages.success(request, 'Objednávka byla označena jako vyzvednutá.')
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'home:index'
        return redirect(next_url)


class OrderDeleteView(View):
    def post(self, request, pk, *args, **kwargs):
        order = get_object_or_404(Order.objects.select_related('customer'), pk=pk)
        customer_name = order.customer.display_name
        order.delete()
        messages.success(request, f'Objednávka pro {customer_name} byla smazána.')
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'home:order-list'
        return redirect(next_url)


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
        return JsonResponse({'errors': flatten_form_errors(form)}, status=400)
