from django.contrib import admin
from .models import Subject, LinkExterno


class LinkExternoInline(admin.TabularInline):
    """
    Permite adicionar links diretamente na página de edição da matéria
    """
    model = LinkExterno
    extra = 1
    fields = ['ordem', 'nome_site', 'url', 'descricao', 'ativo']
    ordering = ['ordem', 'nome_site']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icone', 'total_links']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    inlines = [LinkExternoInline]
    
    def total_links(self, obj):
        """Mostra quantos links a matéria tem"""
        return obj.links_externos.filter(ativo=True).count()
    total_links.short_description = 'Links Ativos'


@admin.register(LinkExterno)
class LinkExternoAdmin(admin.ModelAdmin):
    list_display = ['materia', 'ordem', 'nome_site', 'url', 'ativo', 'adicionado_em']
    list_filter = ['materia', 'ativo', 'adicionado_em']
    search_fields = ['nome_site', 'url', 'descricao']
    ordering = ['materia', 'ordem', 'nome_site']
    list_editable = ['ordem', 'ativo']
    
    def save_model(self, request, obj, form, change):
        """Salva quem adicionou o link"""
        if not change:  # Se está criando
            obj.adicionado_por = request.user
        super().save_model(request, obj, form, change)