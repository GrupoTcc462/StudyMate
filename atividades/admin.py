from django.contrib import admin
from .models import Atividade, AtividadeVisualizacao, AtividadeEnvio, AtividadeSalva


@admin.register(Atividade)
class AtividadeAdmin(admin.ModelAdmin):
    list_display = (
        'titulo', 
        'professor', 
        'tipo', 
        'get_anos_destino_display', 
        'prazo_entrega', 
        'total_visualizacoes',
        'total_envios',
        'criado_em'
    )
    list_filter = ('tipo', 'ano_1', 'ano_2', 'ano_3', 'todos', 'permite_envio', 'criado_em')
    search_fields = ('titulo', 'descricao', 'professor__username')
    readonly_fields = ('criado_em', 'visualizacoes', 'foi_visualizado')
    date_hierarchy = 'criado_em'
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('professor', 'titulo', 'descricao', 'tipo')
        }),
        ('Público-Alvo', {
            'fields': ('ano_1', 'ano_2', 'ano_3', 'todos'),
            'description': 'Selecione para quais anos a atividade será visível'
        }),
        ('Configurações', {
            'fields': ('prazo_entrega', 'permite_envio', 'anexo')
        }),
        ('Estatísticas', {
            'fields': ('criado_em', 'visualizacoes', 'foi_visualizado'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Se não for superuser, mostrar apenas atividades do professor
        if not request.user.is_superuser and request.user.user_type == 'professor':
            qs = qs.filter(professor=request.user)
        return qs
    
    def has_change_permission(self, request, obj=None):
        """
        Bloqueia edição se atividade já foi visualizada (exceto superuser)
        """
        if obj and obj.foi_visualizado and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)
    
    def save_model(self, request, obj, form, change):
        """Define professor automaticamente se não for superuser"""
        if not change and request.user.user_type == 'professor':
            obj.professor = request.user
        super().save_model(request, obj, form, change)


@admin.register(AtividadeVisualizacao)
class AtividadeVisualizacaoAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'atividade', 'visualizado_em')
    list_filter = ('visualizado_em',)
    search_fields = ('aluno__username', 'atividade__titulo')
    readonly_fields = ('visualizado_em',)
    date_hierarchy = 'visualizado_em'


@admin.register(AtividadeEnvio)
class AtividadeEnvioAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'atividade', 'status', 'nota', 'enviado_em')
    list_filter = ('status', 'enviado_em')
    search_fields = ('aluno__username', 'atividade__titulo')
    readonly_fields = ('enviado_em',)
    date_hierarchy = 'enviado_em'
    
    fieldsets = (
        ('Informações do Envio', {
            'fields': ('atividade', 'aluno', 'arquivo', 'status', 'enviado_em')
        }),
        ('Correção (Opcional)', {
            'fields': ('nota', 'feedback'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AtividadeSalva)
class AtividadeSalvaAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'atividade', 'salva_em')
    list_filter = ('salva_em',)
    search_fields = ('aluno__username', 'atividade__titulo')
    readonly_fields = ('salva_em',)
    date_hierarchy = 'salva_em'