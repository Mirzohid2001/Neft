from django.urls import path
from . import views

app_name = 'estokada'

urlpatterns = [
    # Основная панель управления
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Управление операциями
    path('movements/', views.MovementListView.as_view(), name='movement_list'),
    path('movements/<int:pk>/', views.MovementDetailView.as_view(), name='movement_detail'),
    path('movements/<int:pk>/status/<str:status>/', views.change_movement_status, name='change_status'),
    
    # Списки операций по типам
    path('receive/', views.ReceiveListView.as_view(), name='receive_list'),
    path('production/', views.ProductionListView.as_view(), name='production_list'),
    path('transfer/', views.TransferListView.as_view(), name='transfer_list'),
    
    # Формы создания операций (сохраняем для обратной совместимости)
    path('receive/create/', views.ReceiveCreateView.as_view(), name='receive_create'),
    path('production/create/', views.ProductionCreateView.as_view(), name='production_create'),
    path('transfer/create/', views.TransferCreateView.as_view(), name='transfer_create'),
    
    # Обработка заказов от отдела продаж
    path('sales-orders/', views.SalesOrdersListView.as_view(), name='sales_orders'),
    path('sales-orders/<int:pk>/process/', views.process_sales_order, name='process_sales_order'),
] 