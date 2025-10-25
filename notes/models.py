from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
import os

User = get_user_model()

def validate_file_size(file):
    """Valida o tamanho do arquivo (máx 10MB)"""
    max_size = getattr(settings, 'NOTE_MAX_UPLOAD_SIZE', 10 * 1024 * 1024)
    if file.size > max_size:
        raise ValidationError(f'O arquivo não pode ser maior que {max_size/(1024*1024):.0f}MB')

def validate_file_extension(file):
    """Valida a extensão do arquivo"""
    allowed = getattr(settings, 'ALLOWED_FILE_TYPES', ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.txt'])
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed:
        raise ValidationError(f'Extensão {ext} não permitida. Use: {", ".join(allowed)}')


class Subject(models.Model):
    """Modelo centralizado de matérias"""
    name = models.CharField(max_length=60, unique=True, verbose_name='Nome')
    slug = models.SlugField(max_length=80, unique=True, verbose_name='Slug')
    is_active = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Matéria'
        verbose_name_plural = 'Matérias'
        ordering = ['name']

    def __str__(self):
        return self.name


class Note(models.Model):
    """Modelo principal para Notes/Materiais compartilhados"""
    
    FILE_TYPES = [
        ('DOC', 'Documento Word'),
        ('PDF', 'PDF'),
        ('PPT', 'Apresentação'),
        ('LINK', 'Link Externo'),
        ('TXT', 'Texto'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes', verbose_name='Autor')
    title = models.CharField(max_length=150, verbose_name='Título')
    description = models.TextField(max_length=800, blank=True, verbose_name='Descrição')
    file_type = models.CharField(max_length=10, choices=FILE_TYPES, verbose_name='Tipo')
    file = models.FileField(
        upload_to='notes_files/', 
        null=True, 
        blank=True, 
        validators=[validate_file_size, validate_file_extension],
        verbose_name='Arquivo'
    )
    link = models.URLField(null=True, blank=True, verbose_name='Link')
    
    # ALTERADO: agora é ForeignKey para Subject
    subject = models.ForeignKey(
        Subject, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='notes',
        verbose_name='Matéria'
    )
    
    is_recommended = models.BooleanField(default=False, verbose_name='Recomendado')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Criado em')

    # Métricas
    views = models.PositiveIntegerField(default=0, db_index=True, verbose_name='Visualizações')
    likes = models.PositiveIntegerField(default=0, db_index=True, verbose_name='Curtidas')
    downloads = models.PositiveIntegerField(default=0, db_index=True, verbose_name='Downloads')

    class Meta:
        ordering = ['-is_recommended', '-likes', '-views', '-downloads', '-created_at']
        verbose_name = 'Note'
        verbose_name_plural = 'Notes'
        indexes = [
            models.Index(fields=['-likes', '-views']),
            models.Index(fields=['subject']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.title} — {self.author.username}"
    
    def clean(self):
        """Validação customizada"""
        if self.file_type == 'LINK' and not self.link:
            raise ValidationError('Link é obrigatório para tipo LINK')
        if self.file_type != 'LINK' and self.file_type != 'TXT' and not self.file:
            raise ValidationError('Arquivo é obrigatório para este tipo')


class NoteView(models.Model):
    """Registro de visualizações únicas por usuário"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Usuário')
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='views_log', verbose_name='Note')
    viewed_at = models.DateTimeField(auto_now_add=True, verbose_name='Visualizado em')

    class Meta:
        unique_together = ('user', 'note')
        verbose_name = 'Visualização'
        verbose_name_plural = 'Visualizações'
        indexes = [
            models.Index(fields=['note', 'user']),
        ]

    def __str__(self):
        return f"{self.user.username} visualizou {self.note.title}"


class NoteRecommendation(models.Model):
    """Recomendações individuais por professor"""
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='recommendations', verbose_name='Note')
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='given_recommendations',
        verbose_name='Professor'
    )
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, verbose_name='Matéria')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Recomendado em')

    class Meta:
        unique_together = ('note', 'professor')
        verbose_name = 'Recomendação'
        verbose_name_plural = 'Recomendações'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.professor.username} recomendou {self.note.title}"


class Comment(models.Model):
    """Comentários simples em Notes"""
    
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='comments', verbose_name='Note')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Autor')
    text = models.CharField(max_length=400, verbose_name='Comentário')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Comentário'
        verbose_name_plural = 'Comentários'

    def __str__(self):
        return f"{self.author.username}: {self.text[:50]}"


class NoteLike(models.Model):
    """Controle de likes únicos por usuário"""
    
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='note_likes', verbose_name='Note')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Usuário')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Curtido em')

    class Meta:
        unique_together = ('note', 'user')
        verbose_name = 'Like'
        verbose_name_plural = 'Likes'

    def __str__(self):
        return f"{self.user.username} curtiu {self.note.title}"