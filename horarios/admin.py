from django.contrib import admin
from .models import Horario


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ('data_importacao', 'importado_por', 'tipo', 'ativo', 'tamanho_arquivo')
    list_filter = ('tipo', 'ativo', 'data_importacao')
    search_fields = ('importado_por__username',)
    readonly_fields = ('data_importacao', 'tipo')
    date_hierarchy = 'data_importacao'
    
    fieldsets = (
        ('Arquivo', {
            'fields': ('arquivo', 'tipo')
        }),
        ('Informações', {
            'fields': ('importado_por', 'data_importacao', 'ativo')
        }),
    )
    
    def tamanho_arquivo(self, obj):
        """Exibe tamanho do arquivo em MB"""
        try:
            size_mb = obj.arquivo.size / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        except:
            return "N/A"
    tamanho_arquivo.short_description = 'Tamanho'
    
    actions = ['marcar_como_ativo', 'desativar']
    
    def marcar_como_ativo(self, request, queryset):
        """Ativa o horário selecionado e desativa os demais"""
        if queryset.count() > 1:
            self.message_user(request, 'Selecione apenas um horário para ativar', level='error')
            return
        
        Horario.objects.update(ativo=False)
        queryset.update(ativo=True)
        self.message_user(request, 'Horário ativado com sucesso')
    marcar_como_ativo.short_description = '✅ Marcar como ativo'
    
    def desativar(self, request, queryset):
        """Desativa horários selecionados"""
        queryset.update(ativo=False)
        self.message_user(request, f'{queryset.count()} horário(s) desativado(s)')
    desativar.short_description = '❌ Desativar'