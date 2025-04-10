from django.urls import path
from .views import FinancialDashboardView,ChartDataView

app_name = 'accounting'

urlpatterns = [
    path('dashboard/', FinancialDashboardView.as_view(), name='financial_dashboard'),
    path('chart-data/', ChartDataView.as_view(), name='chart_data'),
]
