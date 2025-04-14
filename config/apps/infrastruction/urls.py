from django.urls import path
from . import views

app_name = 'infrastruction'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    
    # Daily Expenses - Receiving
    path('receiving/', views.receiving_list, name='receiving_list'),
    path('receiving/add/', views.receiving_add, name='receiving_add'),
    path('receiving/<int:pk>/', views.receiving_detail, name='receiving_detail'),
    path('receiving/<int:pk>/edit/', views.receiving_edit, name='receiving_edit'),
    path('receiving/<int:pk>/delete/', views.receiving_delete, name='receiving_delete'),
    
    # Daily Expenses - Giving to Workers
    path('giving/', views.giving_list, name='giving_list'),
    path('giving/add/', views.giving_add, name='giving_add'),
    path('giving/<int:pk>/', views.giving_detail, name='giving_detail'),
    path('giving/<int:pk>/edit/', views.giving_edit, name='giving_edit'),
    path('giving/<int:pk>/delete/', views.giving_delete, name='giving_delete'),
    
    # Daily Expenses - Stock
    path('stock/', views.stock_list, name='stock_list'),
    
    # Canteen
    path('canteen/', views.canteen_expenses_list, name='canteen_expenses_list'),
    path('canteen/add/', views.canteen_expense_add, name='canteen_expense_add'),
    path('canteen/<int:pk>/', views.canteen_expense_detail, name='canteen_expense_detail'),
    path('canteen/<int:pk>/edit/', views.canteen_expense_edit, name='canteen_expense_edit'),
    path('canteen/<int:pk>/delete/', views.canteen_expense_delete, name='canteen_expense_delete'),
    path('canteen/report/', views.canteen_monthly_report, name='canteen_monthly_report'),
    
    # Projects
    path('projects/', views.project_list, name='project_list'),
    path('projects/add/', views.project_add, name='project_add'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),
    
    # Project Items
    path('projects/<int:project_pk>/items/add/', views.project_item_add, name='project_item_add'),
    path('projects/<int:project_pk>/items/<int:pk>/edit/', views.project_item_edit, name='project_item_edit'),
    path('projects/<int:project_pk>/items/<int:pk>/delete/', views.project_item_delete, name='project_item_delete'),
] 