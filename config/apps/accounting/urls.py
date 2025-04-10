from django.urls import path
from . import views

app_name = 'accounting'  # Пространство имен для приложения

urlpatterns = [
    # Основные страницы
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings, name='settings'),
    path('export/', views.export_data, name='export'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/create/', views.transaction_create, name='transaction_create'),
    path('transactions/<int:pk>/', views.transaction_detail, name='transaction_detail'),
    path('transactions/<int:pk>/edit/', views.transaction_edit, name='transaction_edit'),
    path('transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/create/', views.account_create, name='account_create'),
    path('accounts/<int:pk>/', views.account_detail, name='account_detail'),
    path('accounts/<int:pk>/edit/', views.account_edit, name='account_edit'),
    path('accounts/<int:pk>/delete/', views.account_delete, name='account_delete'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/', views.category_detail, name='category_detail'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('reports/expense/', views.expense_report, name='expense_report'),
    path('reports/income/', views.income_report, name='income_report'),
    path('reports/cash-flow/', views.cash_flow, name='cash_flow'),
    path('reports/budget/', views.budget, name='budget'),
    path('api/chart-data/', views.chart_data, name='chart_data'),
    path('api/category-data/', views.category_data, name='category_data'),
    path('export/transactions/', views.export_transactions, name='export_transactions'),
    path('export/accounts/', views.export_accounts, name='export_accounts'),
    path('export/report/', views.export_report, name='export_report'),
    path('export/backup/create/', views.create_backup, name='create_backup'),
    path('export/backup/download/<int:pk>/', views.download_backup, name='download_backup'),
    path('export/backup/restore/<int:pk>/', views.restore_backup, name='restore_backup'),
    path('export/backup/delete/<int:pk>/', views.delete_backup, name='delete_backup'),
]
