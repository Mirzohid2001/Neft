"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Place accounts at the beginning to ensure login access
    path('accounts/', include('apps.accounts.urls')),
    path('admin/', admin.site.urls),
    path('', include('apps.dashboard.urls')),
    path('warehouse/', include('apps.warehouse.urls')),
    path('production/', include('apps.production.urls')),
    path('accounting/', include('apps.accounting.urls')),
    path('purchasing/', include('apps.purchasing.urls')),
    path('customs/', include('apps.customs.urls')),
    path('logistics/', include('apps.logistics.urls')),
    path('infrastruction/', include('apps.infrastruction.urls')),
    path('quality_control/', include('apps.quality_control.urls')),
    path('analytics/', include('apps.analytics.urls')),
    path('estokada/', include('apps.estokada.urls')),
    path('sales/', include('apps.sales.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
