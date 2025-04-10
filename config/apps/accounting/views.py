import io
import pandas as pd
from datetime import datetime, timedelta
from django.shortcuts import render
from django.views import View
from django.http import HttpResponse
from .services import create_financial_records, calculate_summary
from .filters import FinancialRecordFilter
from .models import FinancialRecord
from django.db.models import Sum, Q
from django.http import JsonResponse
from apps.warehouse.models import Product, Warehouse
from .utils import send_telegram_message

class FinancialDashboardView(View):
    template_name = 'accounting/dashboard.html'

    def get(self, request):
        filter_type = request.GET.get('filter_type', 'all')

        today = datetime.today()
        date_from, date_to = None, None

        if filter_type == 'today':
            date_from = today
            date_to = today

        elif filter_type == 'week':
            date_from = today - timedelta(days=7)
            date_to = today

        elif filter_type == 'month':
            date_from = today - timedelta(days=30)
            date_to = today

        elif filter_type == 'custom':
            date_from = request.GET.get('date_from')
            date_to = request.GET.get('date_to')

        create_financial_records(date_from, date_to)
        summary = calculate_summary()

        limit = 1000000 
        net_result = summary['net_profit_loss']
        status = summary['status']

        if abs(net_result) >= limit:
            message = f"⚠️ <b>{status}</b>\nSumma: {net_result:,} UZS\nChegara: {limit:,} UZS dan oshdi."
            send_telegram_message(message)

        records = FinancialRecord.objects.all()
        filters = FinancialRecordFilter(request.GET, queryset=records)

        if request.GET.get('export') == 'excel':
            return self.export_excel(filters.qs)

        context = {
            'summary': summary,
            'filter': filters,
            'records': filters.qs,
            'filter_type': filter_type,
            'date_from': date_from,
            'date_to': date_to,
        }
        return render(request, self.template_name, context)

    def export_excel(self, queryset):
        df = pd.DataFrame(list(queryset.values(
            'date', 'product__name', 'warehouse__name',
            'movement_type', 'quantity', 'total_price_sum', 'total_price_usd'
        )))

        df.columns = [
            'Sana', 'Mahsulot', 'Ombor', 'Harakat turi',
            'Miqdor', 'Summa (UZS)', 'Summa (USD)'
        ]

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Moliyaviy Hisobot')

        buffer.seek(0)
        response = HttpResponse(
            buffer, 
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="hisobot.xlsx"'
        return response
    
class ChartDataView(View):

    def get(self, request):
        products = Product.objects.all()
        warehouses = Warehouse.objects.all()

        product_data = []
        for product in products:
            in_sum = FinancialRecord.objects.filter(product=product, movement_type='in').aggregate(Sum('total_price_sum'))['total_price_sum__sum'] or 0
            out_sum = FinancialRecord.objects.filter(product=product, movement_type='out').aggregate(Sum('total_price_sum'))['total_price_sum__sum'] or 0
            product_data.append({
                'product': product.name,
                'in_sum': in_sum,
                'out_sum': out_sum
            })

        warehouse_data = []
        for warehouse in warehouses:
            total = FinancialRecord.objects.filter(warehouse=warehouse).aggregate(Sum('total_price_sum'))['total_price_sum__sum'] or 0
            warehouse_data.append({
                'warehouse': warehouse.name,
                'total_sum': total
            })

        return JsonResponse({'product_data': product_data, 'warehouse_data': warehouse_data})