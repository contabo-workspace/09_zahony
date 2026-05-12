from datetime import datetime

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone

from .models import Customer, Order, OrderItem, RaisedBed


DATE_INPUT_FORMATS = ['%Y-%m-%d', '%d.%m.%Y', '%d. %m. %Y']
TIME_INPUT_FORMATS = ['%H:%M']


def format_czech_date(date_value):
    return f'{date_value.day}. {date_value.month}. {date_value.year}'


class StyledFormMixin:
    input_class = 'form-control'
    textarea_class = 'form-control form-control-textarea'
    select_class = 'form-select'

    def apply_widget_classes(self):
        for field_name, field in self.fields.items():
            widget = field.widget
            existing = widget.attrs.get('class', '')
            if isinstance(widget, forms.Textarea):
                css_class = self.textarea_class
            elif isinstance(widget, forms.Select):
                css_class = self.select_class
            else:
                css_class = self.input_class
            widget.attrs['class'] = f'{existing} {css_class}'.strip()


class CustomerForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['first_name', 'last_name', 'facebook_nickname', 'phone', 'city', 'note']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_widget_classes()


class RaisedBedForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = RaisedBed
        fields = ['name', 'dimensions', 'base_price', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_widget_classes()


class OrderForm(StyledFormMixin, forms.ModelForm):
    ordered_date = forms.DateField(
        label='Datum',
        input_formats=DATE_INPUT_FORMATS,
        widget=forms.DateInput(
            format=DATE_INPUT_FORMATS[0],
            attrs={'type': 'text', 'autocomplete': 'off'},
        ),
    )
    ordered_time = forms.TimeField(
        label='Čas',
        input_formats=TIME_INPUT_FORMATS,
        widget=forms.TimeInput(
            format=TIME_INPUT_FORMATS[0],
            attrs={'type': 'text', 'inputmode': 'numeric'},
        ),
    )
    pickup_date = forms.DateField(
        label='Datum',
        required=False,
        input_formats=DATE_INPUT_FORMATS,
        widget=forms.DateInput(
            format=DATE_INPUT_FORMATS[0],
            attrs={'type': 'text', 'autocomplete': 'off'},
        ),
    )
    pickup_time = forms.TimeField(
        label='Čas',
        required=False,
        input_formats=TIME_INPUT_FORMATS,
        widget=forms.TimeInput(
            format=TIME_INPUT_FORMATS[0],
            attrs={'type': 'text', 'inputmode': 'numeric'},
        ),
    )

    class Meta:
        model = Order
        fields = ['customer', 'status', 'note']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.order_by('last_name', 'first_name')
        self.fields['status'].choices = Order.Status.choices
        self.apply_widget_classes()

        ordered_at = self.initial.get('ordered_at') or getattr(self.instance, 'ordered_at', None)
        pickup_date = self.initial.get('pickup_date') or getattr(self.instance, 'pickup_date', None)
        pickup_time = self.initial.get('pickup_time') or getattr(self.instance, 'pickup_time', None)

        if not self.is_bound:
            now = timezone.localtime(timezone.now())
            ordered_local = timezone.localtime(ordered_at) if ordered_at else now
            self.initial.setdefault('ordered_date', ordered_local.strftime(DATE_INPUT_FORMATS[0]))
            self.initial.setdefault('ordered_time', ordered_local.strftime(TIME_INPUT_FORMATS[0]))
            if pickup_date:
                self.initial.setdefault('pickup_date', pickup_date.strftime(DATE_INPUT_FORMATS[0]))
            if pickup_time:
                self.initial.setdefault('pickup_time', pickup_time.strftime(TIME_INPUT_FORMATS[0]))

    def clean(self):
        cleaned_data = super().clean()
        ordered_date = cleaned_data.get('ordered_date')
        ordered_time = cleaned_data.get('ordered_time')
        pickup_date = cleaned_data.get('pickup_date')
        pickup_time = cleaned_data.get('pickup_time')

        if ordered_date and ordered_time:
            cleaned_data['ordered_at'] = self._combine_to_local_datetime(ordered_date, ordered_time)

        if pickup_time and not pickup_date:
            message = 'Nejdřív vyplň datum vyzvednutí.'
            self.add_error('pickup_date', message)
            self.add_error('pickup_time', message)

        return cleaned_data

    def save(self, commit=True):
        order = super().save(commit=False)
        order.ordered_at = self.cleaned_data['ordered_at']
        order.pickup_date = self.cleaned_data.get('pickup_date')
        order.pickup_time = self.cleaned_data.get('pickup_time')
        if commit:
            order.save()
            self.save_m2m()
        return order

    def _combine_to_local_datetime(self, date_value, time_value):
        naive_value = datetime.combine(date_value, time_value)
        if timezone.is_naive(naive_value):
            return timezone.make_aware(naive_value, timezone.get_current_timezone())
        return naive_value


class OrderItemForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['raised_bed', 'quantity', 'unit_price']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['raised_bed'].queryset = RaisedBed.objects.filter(is_active=True).order_by('name', 'dimensions')
        self.fields['unit_price'].localize = False
        self.fields['unit_price'].widget.is_localized = False
        self.apply_widget_classes()


class BaseOrderItemFormSet(BaseInlineFormSet):
    default_error_messages = {
        **BaseInlineFormSet.default_error_messages,
        'too_few_forms': 'Přidejte alespoň jednu položku.',
    }


OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    formset=BaseOrderItemFormSet,
    form=OrderItemForm,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True,
)