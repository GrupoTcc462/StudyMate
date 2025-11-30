from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
import os

User = get_user_model()


def validate_file_size_horario(file):
    """Valida tamanho máximo de 5MB"""
    max_size = 5 * 1024 * 1024  # 5MB
    if file.size > max_size:
        raise ValidationError('O arquivo não pode ser maior que 5MB')


def validate_file_extension_horario(file):
    """Valida extensões permitidas"""
    ext = os.path.splitext(file.name)[1].lower()
    allowed = ['.jpg', '.jpeg', '.png', '.xlsx', '.xls']
    if ext not in allowed:
        raise ValidationError(f'Extensão {ext} não permitida. Use: {", ".join(allowed)}')


class Horario(models.Model):
    """
    Modelo para armazenar horários das turmas.
    Professores/admins podem importar imagens ou planilhas Excel.
    """
    
    TIPO_CHOICES = [
        ('IMAGEM', 'Imagem'),
        ('EXCEL', 'Planilha Excel'),
    ]
    
    # Quem importou
    importado_por = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='horarios_importados',
        verbose_name='Importado por'
    )
    
    # Arquivo
    arquivo = models.FileField(
        upload_to='horarios/',
        validators=[validate_file_size_horario, validate_file_extension_horario],
        verbose_name='Arquivo'
    )
    
    # Tipo detectado automaticamente
    tipo = models.CharField(
        max_length=10, 
        choices=TIPO_CHOICES,
        verbose_name='Tipo'
    )
    
    # Metadados
    data_importacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de importação'
    )
    
    # Controle de versão (o mais recente é o ativo)
    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )
    
    class Meta:
        verbose_name = 'Horário'
        verbose_name_plural = 'Horários'
        ordering = ['-data_importacao']
    
    def __str__(self):
        return f"Horário de {self.data_importacao.strftime('%d/%m/%Y %H:%M')} por {self.importado_por.username}"
    
    def save(self, *args, **kwargs):
        # Detectar tipo automaticamente
        ext = os.path.splitext(self.arquivo.name)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png']:
            self.tipo = 'IMAGEM'
        elif ext in ['.xlsx', '.xls']:
            self.tipo = 'EXCEL'
        
        # Desativar horários anteriores ao salvar novo
        if self.ativo:
            Horario.objects.filter(ativo=True).update(ativo=False)
        
        super().save(*args, **kwargs)
    
    def get_extensao(self):
        """Retorna extensão do arquivo"""
        return os.path.splitext(self.arquivo.name)[1].lower()