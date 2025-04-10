from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomUserChangeForm

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = (
        'username', 
        'last_name', 
        'first_name', 
        'middle_name',
        'role',
        'job_position', 
        'phone_number',
        'is_verified', 
        'is_staff', 
        'is_active'
    )
    
    list_filter = (
        'role',
        'is_staff', 
        'is_active', 
        'is_verified', 
        'job_position', 
        'groups'
    )

    fieldsets = (
        ('Фойдаланувчи кириш маълумотлари', {
            'fields': ('username', 'password')
        }),
        ('Шахсий маълумотлар', {
            'fields': (
                'last_name', 
                'first_name', 
                'middle_name', 
                'photo',
                'date_of_birth', 
                'address', 
                'phone_number'
            )
        }),
        ('Ишга оид маълумотлар', {
            'fields': (
                'role',
                'job_position',
                'date_joined_company', 
                'notes'
            )
        }),
        ('Рухсатлар ва тасдиқлаш', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions')
        }),
        ('Муҳим саналар', {
            'fields': ('last_login', 'date_joined')
        }),
    )

    add_fieldsets = (
        ('Янги фойдаланувчи яратиш', {
            'classes': ('wide',),
            'fields': (
                'username', 
                'password1', 
                'password2', 
                'first_name', 
                'last_name', 
                'middle_name',
                'role',
                'job_position',
                'phone_number',
                'is_verified', 
                'is_active', 
                'is_staff',
                'groups'
            ),
        }),
    )

    search_fields = ('username', 'first_name', 'last_name', 'middle_name', 'job_position', 'phone_number')
    ordering = ('username',)

admin.site.register(CustomUser, CustomUserAdmin)
