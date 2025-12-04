from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
import os

User = get_user_model()

def validate_file_size(file):
    """
    🔥 VALIDAÇÃO ATUALIZADA: Máximo 50MB
    """
    from django.conf import settings
    max_size = getattr(settings, 'NOTE_MAX_UPLOAD_SIZE', 50 * 1024 * 1024)
    if file.size > max_size:
        raise ValidationError(f'⚠️ O arquivo excede o limite de {max_size/(1024*1024):.0f}MB.')

def validate_file_extension(file):
    """
    Valida a extensão do arquivo
    """
    from django.conf import settings
    allowed = getattr(settings, 'ALLOWED_FILE_TYPES', ['.pdf', '.doc', '.docx', '.ppt', '.pptx'])
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed:
        raise ValidationError(f'❌ Extensão {ext} não permitida. Use: {", ".join(allowed)}')


class Materia(models.Model):
    """
    Model de matérias EXCLUSIVO para o sistema de Notes.
    """
    nome = models.CharField(max_length=100, unique=True, verbose_name='Nome da Matéria')
    
    class Meta:
        verbose_name = 'Matéria (Notes)'
        verbose_name_plural = 'Matérias (Notes)'
        ordering = ['nome']
    
    def __str__(self):
        return self.nome


class Note(models.Model):
    """Modelo principal para Notes/Materiais compartilhados"""
    
    FILE_TYPES = [
        ('DOC', 'Documento Word'),
        ('PDF', 'PDF'),
        ('PPT', 'Apresentação'),
        ('LINK', 'Link Externo'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes', verbose_name='Autor')
    title = models.CharField(max_length=50, verbose_name='Título')
    description = models.TextField(max_length=400, blank=True, verbose_name='Descrição')
    file_type = models.CharField(max_length=10, choices=FILE_TYPES, verbose_name='Tipo')
    file = models.FileField(
        upload_to='notes_files/', 
        null=True, 
        blank=True, 
        validators=[validate_file_size, validate_file_extension],
        verbose_name='Arquivo'
    )
    link = models.URLField(null=True, blank=True, verbose_name='Link')
    
    subject_new = models.ForeignKey(
        Materia, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='Matéria',
        related_name='notes'
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
            models.Index(fields=['subject_new']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.title} — {self.author.username}"
    
    def clean(self):
        """
        🔥 VALIDAÇÃO CUSTOMIZADA APRIMORADA
        """
        # Validação: Link obrigatório para tipo LINK
        if self.file_type == 'LINK' and not self.link:
            raise ValidationError('❌ Link é obrigatório quando o tipo é "Link Externo".')
        
        # Validação: Arquivo obrigatório para outros tipos
        if self.file_type != 'LINK' and not self.file:
            raise ValidationError('❌ Arquivo é obrigatório para este tipo de conteúdo.')
    
    def check_auto_recommend(self):
        """
        Verifica se o note atingiu os critérios para recomendação automática
        """
        if not self.is_recommended:
            if self.downloads >= 20 or self.likes >= 40 or self.views >= 50:
                self.is_recommended = True
                self.save(update_fields=['is_recommended'])


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


class NoteView(models.Model):
    """Controle de visualizações únicas por usuário"""
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='note_views', verbose_name='Note')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Usuário')
    viewed_at = models.DateTimeField(auto_now_add=True, verbose_name='Visualizado em')

    class Meta:
        unique_together = ('note', 'user')
        verbose_name = 'Visualização'
        verbose_name_plural = 'Visualizações'
        indexes = [
            models.Index(fields=['note', 'user']),
            models.Index(fields=['-viewed_at']),
        ]

    def __str__(self):
        return f"{self.user.username} visualizou {self.note.title}"


class NoteRecommendation(models.Model):
    """Sistema de recomendações manuais por professores"""
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='recommendations', verbose_name='Note')
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'professor'}, verbose_name='Professor')
    recommended_at = models.DateTimeField(auto_now_add=True, verbose_name='Recomendado em')

    class Meta:
        unique_together = ('note', 'teacher')
        verbose_name = 'Recomendação'
        verbose_name_plural = 'Recomendações'
        ordering = ['-recommended_at']

    def __str__(self):
        return f"{self.teacher.username} recomendou {self.note.title}"