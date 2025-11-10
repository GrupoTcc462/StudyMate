from django.contrib import admin
from .models import PerfilUsuario


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('user', 'last_name_change', 'pode_alterar_nome')
    search_fields = ('user__username',)
    readonly_fields = ('last_name_change',)
    
    def pode_alterar_nome(self, obj):
        return "✅ Sim" if obj.pode_alterar_nome() else f"❌ Não (falta {obj.dias_ate_proxima_mudanca()} dias)"
    pode_alterar_nome.short_description = 'Pode alterar nome?'