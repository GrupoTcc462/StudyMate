from django.contrib import admin

from django.contrib import admin
from .models import Note, Comment, NoteLike

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'file_type', 'subject', 'is_recommended', 'views', 'likes', 'downloads', 'created_at')
    list_filter = ('file_type', 'subject', 'is_recommended', 'created_at')
    search_fields = ('title', 'description', 'author__username')
    readonly_fields = ('views', 'likes', 'downloads', 'created_at')
    list_editable = ('is_recommended',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('author', 'title', 'description', 'subject')
        }),
        ('Conteúdo', {
            'fields': ('file_type', 'file', 'link')
        }),
        ('Configurações', {
            'fields': ('is_recommended',)
        }),
        ('Métricas', {
            'fields': ('views', 'likes', 'downloads', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_recommended', 'unmark_as_recommended']
    
    def mark_as_recommended(self, request, queryset):
        queryset.update(is_recommended=True)
        self.message_user(request, f'{queryset.count()} note(s) marcado(s) como recomendado(s)')
    mark_as_recommended.short_description = 'Marcar como recomendado'
    
    def unmark_as_recommended(self, request, queryset):
        queryset.update(is_recommended=False)
        self.message_user(request, f'{queryset.count()} note(s) desmarcado(s)')
    unmark_as_recommended.short_description = 'Desmarcar como recomendado'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'note', 'text_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('text', 'author__username', 'note__title')
    readonly_fields = ('created_at',)
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Comentário'


@admin.register(NoteLike)
class NoteLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'note', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'note__title')
    readonly_fields = ('created_at',)