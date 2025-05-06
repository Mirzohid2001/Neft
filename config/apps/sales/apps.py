from django.apps import AppConfig


class SalesConfig(AppConfig):
       default_auto_field = 'django.db.models.BigAutoField'
       name = 'apps.sales'
       verbose_name = 'Продажи'
       
       def ready(self):
           # Импортируем сигналы при загрузке приложения
           import apps.sales.signals
