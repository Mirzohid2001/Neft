from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = (
            'username', 
            'first_name', 
            'last_name', 
            'middle_name', 
            'phone_number', 
            'job_position',
            'photo',
            'date_of_birth',
            'date_joined_company', 
            'address',
            'is_verified', 
            'groups'
        )

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = (
            'username', 
            'first_name', 
            'last_name', 
            'middle_name', 
            'phone_number', 
            'job_position',
            'photo',
            'date_of_birth',
            'date_joined_company', 
            'address',
            'is_verified', 
            'groups'
        )
