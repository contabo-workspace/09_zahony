from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone

from .models import Customer, Order, OrderItem, RaisedBed


DATETIME_INPUT_FORMATS = ['%Y-%m-%dT%H:%M']


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
            widget.attrs.setdefault('placeholder', field.label)


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
    ordered_at = forms.DateTimeField(
        label='Objednáno dne',
        input_formats=DATETIME_INPUT_FORMATS,
        widget=forms.DateTimeInput(format=DATETIME_INPUT_FORMATS[0], attrs={'type': 'datetime-local'}),
    )
    pickup_at = forms.DateTimeField(
        label='Vyzvednutí dne a čas',
        required=False,
        input_formats=DATETIME_INPUT_FORMATS,
        widget=forms.DateTimeInput(format=DATETIME_INPUT_FORMATS[0], attrs={'type': 'datetime-local'}),
    )

    class Meta:
        model = Order
        fields = ['customer', 'ordered_at', 'pickup_at', 'status', 'note']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.order_by('last_name', 'first_name')
        self.fields['status'].choices = Order.Status.choices
        self.apply_widget_classes()
        if not self.is_bound:
            now = timezone.localtime(timezone.now())
            self.initial.setdefault('ordered_at', now.strftime(DATETIME_INPUT_FORMATS[0]))


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
        self.apply_widget_classes()


OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True,
)