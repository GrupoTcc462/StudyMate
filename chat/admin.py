from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Chat, Mensagem, MensagemApagada


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'remetente', 'destinatario', 'data_criacao', 'total_mensagens')
    list_filter = ('data_criacao',)
    search_fields = ('remetente__username', 'destinatario__username')
    readonly_fields = ('data_criacao',)
    date_hierarchy = 'data_criacao'
    
    def total_mensagens(self, obj):
        return obj.mensagens.count()
    total_mensagens.short_description = 'Total de Mensagens'


@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ('id', 'remetente', 'chat', 'mensagem_preview', 'lida', 'data_envio')
    list_filter = ('lida', 'data_envio')
    search_fields = ('remetente__username', 'mensagem')
    readonly_fields = ('data_envio', 'data_leitura')
    date_hierarchy = 'data_envio'
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('chat', 'remetente', 'mensagem', 'anexo')
        }),
        ('Status', {
            'fields': ('lida', 'data_envio', 'data_leitura')
        }),
    )
    
    def mensagem_preview(self, obj):
        return obj.mensagem[:50] + '...' if len(obj.mensagem) > 50 else obj.mensagem
    mensagem_preview.short_description = 'Mensagem'


@admin.register(MensagemApagada)
class MensagemApagadaAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'mensagem', 'data_apagada')
    list_filter = ('data_apagada',)
    search_fields = ('usuario__username', 'mensagem__mensagem')
    readonly_fields = ('data_apagada',)
    date_hierarchy = 'data_apagada'