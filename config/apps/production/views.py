from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse, reverse_lazy
from django.db.models import Sum
from django.contrib import messages
from django.utils import timezone

from .models import (
    ProductionProcess, RawMaterialProcessing, GasolineMixing,
    ProductionInput, ProductionOutput, ProductionType
)
from .forms import (
    ProductionProcessForm, RawMaterialProcessingForm, GasolineMixingForm,
    ProductionInputForm, ProductionOutputForm, ProductionTypeForm
)

def index(request):
    """Главная страница производственного модуля"""
    raw_processing_count = RawMaterialProcessing.objects.count()
    gasoline_mixing_count = GasolineMixing.objects.count()
    
    context = {
        'raw_processing_count': raw_processing_count,
        'gasoline_mixing_count': gasoline_mixing_count,
    }
    return render(request, 'production/index.html', context)

# Представления для производственных процессов
class ProductionProcessListView(ListView):
    model = ProductionProcess
    template_name = 'production/process_list.html'
    context_object_name = 'processes'
    ordering = ['-start_date']

class ProductionProcessDetailView(DetailView):
    model = ProductionProcess
    template_name = 'production/process_detail.html'
    context_object_name = 'process'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        process = self.get_object()
        
        # Добавление связанных данных в зависимости от типа процесса
        if process.process_type == 'raw_processing':
            try:
                context['raw_processing'] = process.raw_processing
            except RawMaterialProcessing.DoesNotExist:
                pass
        elif process.process_type == 'mixing':
            try:
                context['gasoline_mixing'] = process.gasoline_mixing
            except GasolineMixing.DoesNotExist:
                pass
        
        # Получение входных и выходных материалов
        context['inputs'] = process.inputs.all()
        context['outputs'] = process.outputs.all()
        
        return context

class ProductionProcessCreateView(CreateView):
    model = ProductionProcess
    form_class = ProductionProcessForm
    template_name = 'production/process_create.html'
    
    def get_success_url(self):
        process = self.object
        if process.process_type == 'raw_processing':
            return reverse('production:raw_processing_create', kwargs={'process_id': process.id})
        else:
            return reverse('production:gasoline_mixing_create', kwargs={'process_id': process.id})

# Представления для переработки сырья
class RawMaterialProcessingCreateView(CreateView):
    model = RawMaterialProcessing
    form_class = RawMaterialProcessingForm
    template_name = 'production/raw_processing_create.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        process_id = self.kwargs.get('process_id')
        context['process'] = get_object_or_404(ProductionProcess, id=process_id)
        return context
    
    def form_valid(self, form):
        process_id = self.kwargs.get('process_id')
        process = get_object_or_404(ProductionProcess, id=process_id)
        form.instance.production_process = process
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('production:process_detail', kwargs={'pk': self.object.production_process.id})

# Представления для производства бензина
class GasolineMixingCreateView(CreateView):
    model = GasolineMixing
    form_class = GasolineMixingForm
    template_name = 'production/gasoline_mixing_create.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        process_id = self.kwargs.get('process_id')
        context['process'] = get_object_or_404(ProductionProcess, id=process_id)
        return context
    
    def form_valid(self, form):
        process_id = self.kwargs.get('process_id')
        process = get_object_or_404(ProductionProcess, id=process_id)
        form.instance.production_process = process
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('production:process_detail', kwargs={'pk': self.object.production_process.id})

# Представления для входящих материалов
class ProductionInputCreateView(CreateView):
    model = ProductionInput
    form_class = ProductionInputForm
    template_name = 'production/input_create.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        process_id = self.kwargs.get('process_id')
        context['process'] = get_object_or_404(ProductionProcess, id=process_id)
        return context
    
    def form_valid(self, form):
        process_id = self.kwargs.get('process_id')
        process = get_object_or_404(ProductionProcess, id=process_id)
        form.instance.production_process = process
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('production:process_detail', kwargs={'pk': self.object.production_process.id})

# Представления для исходящих материалов
class ProductionOutputCreateView(CreateView):
    model = ProductionOutput
    form_class = ProductionOutputForm
    template_name = 'production/output_create.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        process_id = self.kwargs.get('process_id')
        context['process'] = get_object_or_404(ProductionProcess, id=process_id)
        return context
    
    def form_valid(self, form):
        process_id = self.kwargs.get('process_id')
        process = get_object_or_404(ProductionProcess, id=process_id)
        form.instance.production_process = process
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('production:process_detail', kwargs={'pk': self.object.production_process.id})

# Завершение производственного процесса
def complete_process(request, pk):
    process = get_object_or_404(ProductionProcess, pk=pk)
    if request.method == 'POST':
        process.end_date = timezone.now()
        process.save()
        messages.success(request, "Ishlab chiqarish jarayoni muvaffaqiyatli tugatildi!")
        return redirect('production:process_detail', pk=process.pk)
    return render(request, 'production/complete_process.html', {'process': process})
