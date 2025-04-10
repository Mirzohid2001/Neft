from django.urls import path
from . import views

app_name = 'production'

urlpatterns = [
    path('', views.index, name='index'),
    
    # Производственные процессы
    path('processes/', views.ProductionProcessListView.as_view(), name='process_list'),
    path('processes/<int:pk>/', views.ProductionProcessDetailView.as_view(), name='process_detail'),
    path('processes/create/', views.ProductionProcessCreateView.as_view(), name='process_create'),
    path('processes/<int:pk>/complete/', views.complete_process, name='complete_process'),
    
    # Переработка сырья
    path('processes/<int:process_id>/raw-processing/create/', 
         views.RawMaterialProcessingCreateView.as_view(), name='raw_processing_create'),
    
    # Производство бензина
    path('processes/<int:process_id>/gasoline-mixing/create/', 
         views.GasolineMixingCreateView.as_view(), name='gasoline_mixing_create'),
    
    # Входящие и исходящие материалы
    path('processes/<int:process_id>/inputs/create/', 
         views.ProductionInputCreateView.as_view(), name='input_create'),
    path('processes/<int:process_id>/outputs/create/', 
         views.ProductionOutputCreateView.as_view(), name='output_create'),
]