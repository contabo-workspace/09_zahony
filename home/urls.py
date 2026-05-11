from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.HomePageView.as_view(), name='index'),
    path('objednavky/', views.OrderListView.as_view(), name='order-list'),
    path('objednavky/nova/', views.OrderCreateView.as_view(), name='order-create'),
    path('objednavky/<int:pk>/smazat/', views.OrderDeleteView.as_view(), name='order-delete'),
    path('objednavky/<int:pk>/vyzvednuto/', views.OrderMarkPickedUpView.as_view(), name='order-mark-picked-up'),
    path('modals/objednavky/<int:pk>/upravit/', views.OrderModalUpdateView.as_view(), name='order-modal-update'),
    path('modals/zakaznici/vytvorit/', views.CustomerModalCreateView.as_view(), name='customer-modal-create'),
    path('modals/zahony/vytvorit/', views.RaisedBedModalCreateView.as_view(), name='raised-bed-modal-create'),
]
