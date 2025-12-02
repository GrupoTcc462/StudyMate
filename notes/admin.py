from django.contrib import admin
from .models import Materia, Note, Comment, NoteLike, NoteView, NoteRecommendation


# ========================================
# NOVO ADMIN: MATÉRIAS DO NOTES
# ========================================
@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    """Admin para cadastro de matérias exclusivas do Notes"""
    list_display = ('id', 'nome', 'total_notes')
    search_fields = ('nome',)
    ordering = ('nome',)
    
    def total_notes(self, obj):
        """Conta quantos notes usam essa matéria"""
        return obj.notes.count()
    total_notes.short_description = 'Total de Notes'


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'file_type', 'get_subject', 'is_recommended', 'views', 'likes', 'downloads', 'created_at')
    list_filter = ('file_type', 'subject_new', 'is_recommended', 'created_at', 'author__user_type')
    search_fields = ('title', 'description', 'author__username', 'subject_new__nome')
    readonly_fields = ('views', 'likes', 'downloads', 'created_at')
    list_editable = ('is_recommended',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('author', 'title', 'description', 'subject_new')
        }),
        ('Conteúdo', {
            'fields': ('file_type', 'file', 'link')
        }),
        ('Configurações', {
            'fields': ('is_recommended',),
            'description': 'Apenas professores e administradores podem marcar notes como recomendados.'
        }),
        ('Métricas', {
            'fields': ('views', 'likes', 'downloads', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_recommended', 'unmark_as_recommended']
    
    def get_subject(self, obj):
        """Exibe o nome da matéria"""
        return obj.subject_new.nome if obj.subject_new else '—'
    get_subject.short_description = 'Matéria'
    
    def mark_as_recommended(self, request, queryset):
        """Ação para marcar notes como recomendados"""
        if not (request.user.user_type == 'professor' or request.user.is_staff):
            self.message_user(request, 'Apenas professores podem marcar notes como recomendados', level='error')
            return
        
        updated = queryset.update(is_recommended=True)
        self.message_user(request, f'{updated} note(s) marcado(s) como recomendado(s)')
    mark_as_recommended.short_description = '⭐ Marcar como recomendado'
    
    def unmark_as_recommended(self, request, queryset):
        """Ação para desmarcar notes como recomendados"""
        updated = queryset.update(is_recommended=False)
        self.message_user(request, f'{updated} note(s) desmarcado(s)')
    unmark_as_recommended.short_description = '❌ Desmarcar como recomendado'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'note', 'text_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('text', 'author__username', 'note__title')
    readonly_fields = ('created_at',)
    
    def text_preview(self, obj):
        """Exibe prévia do comentário"""
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Comentário'


@admin.register(NoteLike)
class NoteLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'note', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'note__title')
    readonly_fields = ('created_at',)


@admin.register(NoteView)
class NoteViewAdmin(admin.ModelAdmin):
    """Admin para visualizações únicas de notes"""
    list_display = ('user', 'note', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('user__username', 'note__title')
    readonly_fields = ('viewed_at',)
    date_hierarchy = 'viewed_at'


@admin.register(NoteRecommendation)
class NoteRecommendationAdmin(admin.ModelAdmin):
    """Admin para recomendações de professores"""
    list_display = ('teacher', 'note', 'recommended_at')
    list_filter = ('recommended_at', 'teacher')
    search_fields = ('teacher__username', 'note__title')
    readonly_fields = ('recommended_at',)
    date_hierarchy = 'recommended_at'


# Personalização do Admin Site
admin.site.site_header = "StudyMate - Administração"
admin.site.site_title = "StudyMate Admin"
admin.site.index_title = "Painel de Controle"