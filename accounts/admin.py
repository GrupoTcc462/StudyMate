from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Informações Adicionais', {'fields': ('user_type', 'matricula', 'telefone')}),
    )
    list_display = ('username', 'email', 'user_type', 'is_staff')
