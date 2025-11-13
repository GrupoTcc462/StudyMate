from django.contrib import admin
from .models import PerfilUsuario


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('user', 'last_edit', 'streak_count', 'pode_editar_status')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('last_edit', 'last_login_date', 'streak_count')
    list_filter = ('last_login_date',)
    
    fieldsets = (
        ('Usuário', {
            'fields': ('user', 'photo')
        }),
        ('Controle de Edições', {
            'fields': ('last_edit',),
            'description': 'Usuários podem editar o perfil a cada 7 dias (exceto superusers)'
        }),
        ('Frequência (Streak)', {
            'fields': ('last_login_date', 'streak_count'),
            'classes': ('collapse',)
        }),
    )
    
    def pode_editar_status(self, obj):
        if obj.user.is_superuser:
            return "✅ Sim (Superuser)"
        elif obj.pode_editar():
            return "✅ Sim"
        else:
            return f"❌ Não (falta {obj.dias_ate_proxima_edicao()} dias)"
    pode_editar_status.short_description = 'Pode editar?'