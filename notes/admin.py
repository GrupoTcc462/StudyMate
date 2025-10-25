from django.contrib import admin
from .models import Note, Comment, NoteLike, Subject, NoteView, NoteRecommendation


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'notes_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active',)
    
    def notes_count(self, obj):
        return obj.notes.count()
    notes_count.short_description = 'Nº de Notes'


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'file_type', 'subject', 'is_recommended', 'views', 'likes', 'downloads', 'created_at')
    list_filter = ('file_type', 'subject', 'is_recommended', 'created_at')
    search_fields = ('title', 'description', 'author__username')
    readonly_fields = ('views', 'likes', 'downloads', 'created_at')
    list_editable = ('is_recommended',)
    date_hierarchy = 'created_at'
    autocomplete_fields = ['subject']
    
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


@admin.register(NoteView)
class NoteViewAdmin(admin.ModelAdmin):
    list_display = ('user', 'note', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('user__username', 'note__title')
    readonly_fields = ('user', 'note', 'viewed_at')
    date_hierarchy = 'viewed_at'
    
    def has_add_permission(self, request):
        return False  # Views são criadas automaticamente


@admin.register(NoteRecommendation)
class NoteRecommendationAdmin(admin.ModelAdmin):
    list_display = ('professor', 'note', 'subject', 'created_at')
    list_filter = ('subject', 'created_at')
    search_fields = ('professor__username', 'note__title')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    autocomplete_fields = ['note', 'subject']


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