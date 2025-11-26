from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Subject(models.Model):
    """Matéria (ex: Matemática)"""
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Content(models.Model):
    CONTENT_TYPES = [
        ('map', 'Mapa Mental'),
        ('res', 'Resumo'),
        ('vid', 'Vídeoaula'),
        ('exe', 'Lista de Exercícios'),
        ('doc', 'PDF/Doc'),
        ('other', 'Outro'),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='contents')
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPES)
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    external_url = models.URLField(blank=True, help_text="Link do vídeo/external resource (opcional)")
    file = models.FileField(upload_to='materias/files/%Y/%m/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='materias/thumbs/%Y/%m/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    recommended = models.BooleanField(default=False)

    class Meta:
        ordering = ['-recommended', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_content_type_display()})"
