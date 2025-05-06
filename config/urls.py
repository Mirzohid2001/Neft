from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('warehouse/', include('warehouse.urls')),
    path('sales/', include('apps.sales.urls')),
    path('estokada/', include('apps.estokada.urls')),
] 