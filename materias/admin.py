from django.contrib import admin
from .models import Subject, Content

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'content_type', 'created_by', 'created_at', 'recommended')
    list_filter = ('content_type', 'subject', 'recommended')
    search_fields = ('title', 'description')
