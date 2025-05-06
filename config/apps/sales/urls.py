from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Основная панель управления
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Маршруты для заказов
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/edit/', views.OrderUpdateView.as_view(), name='order_update'),
    path('orders/<int:pk>/delete/', views.OrderDeleteView.as_view(), name='order_delete'),
    
    # Маршруты для товарных позиций заказов
    path('order-items/add/<int:order_id>/', views.OrderItemCreateView.as_view(), name='add_order_item'),
    path('order-items/<int:pk>/edit/', views.OrderItemUpdateView.as_view(), name='edit_order_item'),
    path('order-items/<int:pk>/delete/', views.OrderItemDeleteView.as_view(), name='delete_order_item'),
    
    # Маршруты для платежей
    path('payments/add/<int:order_id>/', views.PaymentCreateView.as_view(), name='add_payment'),
    path('payments/<int:pk>/edit/', views.PaymentUpdateView.as_view(), name='edit_payment'),
    path('payments/<int:pk>/delete/', views.PaymentDeleteView.as_view(), name='delete_payment'),
    
    # AJAX маршруты 
    path('ajax/get-client-contracts/', views.get_client_contracts, name='get_client_contracts'),
    path('ajax/get-product-price/', views.get_product_price, name='get_product_price'),
    
    # Маршруты для клиентов
    path('clients/', views.ClientListView.as_view(), name='client_list'),
    path('clients/create/', views.ClientCreateView.as_view(), name='client_create'),
    
    # Маршруты для контрактов
    path('contracts/', views.ContractListView.as_view(), name='contract_list'),
    path('contracts/create/', views.ContractCreateView.as_view(), name='contract_create'),
    
    # Маршруты для управления продажами (базовые представления)
    path('sales-list/', views.SalesListView.as_view(), name='sales_list'),
    path('sales-create/', views.SalesCreateView.as_view(), name='sales_create'),
    path('sales-detail/<int:pk>/', views.SalesDetailView.as_view(), name='sales_detail'),
    path('sales-edit/<int:pk>/', views.SalesUpdateView.as_view(), name='sales_edit'),
    path('sales-stats/', views.SalesStatsView.as_view(), name='sales_stats'),
    
    # Маршруты для типов операций
    path('reception/create/', views.ReceptionCreateView.as_view(), name='reception_create'),
    path('sale/create/', views.SalesCreateView.as_view(), name='sale_create'),
    path('transfer/create/', views.TransferCreateView.as_view(), name='transfer_create'),
    path('production/create/', views.ProductionCreateView.as_view(), name='production_create'),
    path('movements/', views.MovementListView.as_view(), name='movement_list'),
    
    # Маршруты для отчетов - закомментированы, так как классы не существуют в views.py
    # path('reports/daily/', views.DailyReportView.as_view(), name='daily_report'),
    # path('reports/monthly/', views.MonthlyReportView.as_view(), name='monthly_report'),
    # path('reports/product/', views.ProductReportView.as_view(), name='product_report'),
    # path('reports/client/', views.ClientReportView.as_view(), name='client_report'),
    
    # API для графиков
    path('chart-data/', views.SalesChartDataView.as_view(), name='chart_data'),
] 