from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
import os

User = get_user_model()


def validate_file_size_atividade(file):
    """Valida o tamanho do arquivo (máx 10MB)"""
    max_size = 10 * 1024 * 1024  # 10MB
    if file.size > max_size:
        raise ValidationError(f'O arquivo não pode ser maior que 10MB')


def validate_file_extension_atividade(file):
    """Valida a extensão do arquivo"""
    allowed = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.zip']
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed:
        raise ValidationError(f'Extensão {ext} não permitida. Use: {", ".join(allowed)}')


class Atividade(models.Model):
    """
    Modelo para atividades acadêmicas criadas por professores
    """
    
    TIPO_CHOICES = [
        ('ATIVIDADE', 'Atividade'),
        ('AVISO_PROVA', 'Aviso de Prova'),
        ('AVISO_SIMPLES', 'Aviso Simples'),
    ]
    
    ANO_CHOICES = [
        ('1', '1º Ano'),
        ('2', '2º Ano'),
        ('3', '3º Ano'),
        ('TODOS', 'Todos'),
    ]
    
    # Informações básicas
    professor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='atividades_criadas',
        limit_choices_to={'user_type': 'professor'},
        verbose_name='Professor'
    )
    titulo = models.CharField(max_length=50, verbose_name='Título')
    
    # DESCRIÇÃO SEM LIMITE CONFORME RELATÓRIO
    descricao = models.TextField(blank=True, verbose_name='Descrição/Orientações')
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo de Atividade')
    
    # Público-alvo (pode ser múltiplo)
    ano_1 = models.BooleanField(default=False, verbose_name='1º Ano')
    ano_2 = models.BooleanField(default=False, verbose_name='2º Ano')
    ano_3 = models.BooleanField(default=False, verbose_name='3º Ano')
    todos = models.BooleanField(default=False, verbose_name='Todos os Anos')
    
    # Configurações
    prazo_entrega = models.DateTimeField(null=True, blank=True, verbose_name='Prazo de Entrega')
    permite_envio = models.BooleanField(default=True, verbose_name='Permite Envio pelo Aluno')
    
    # Anexo opcional
    anexo = models.FileField(
        upload_to='atividades_anexos/',
        null=True,
        blank=True,
        validators=[validate_file_size_atividade, validate_file_extension_atividade],
        verbose_name='Anexo'
    )
    
    # Controle
    criado_em = models.DateTimeField(default=timezone.now, verbose_name='Criado em')
    visualizacoes = models.PositiveIntegerField(default=0, verbose_name='Visualizações')
    foi_visualizado = models.BooleanField(default=False, verbose_name='Foi Visualizado por Algum Aluno')
    
    class Meta:
        verbose_name = 'Atividade'
        verbose_name_plural = 'Atividades'
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"{self.titulo} - {self.professor.username}"
    
    def clean(self):
        """Validações customizadas"""
        # Aviso de prova e aviso simples não permitem envio
        if self.tipo in ['AVISO_PROVA', 'AVISO_SIMPLES']:
            self.permite_envio = False
        
        # Pelo menos um público deve ser selecionado
        if not any([self.ano_1, self.ano_2, self.ano_3, self.todos]):
            raise ValidationError('Selecione pelo menos um ano ou "Todos".')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_anos_destino(self):
        """Retorna lista de anos para quem a atividade é destinada"""
        if self.todos:
            return ['1º Ano', '2º Ano', '3º Ano']
        
        anos = []
        if self.ano_1:
            anos.append('1º Ano')
        if self.ano_2:
            anos.append('2º Ano')
        if self.ano_3:
            anos.append('3º Ano')
        return anos
    
    def get_anos_destino_display(self):
        """Retorna string formatada dos anos"""
        if self.todos:
            return 'Todos os Anos'
        return ', '.join(self.get_anos_destino())
    
    def esta_encerrada(self):
        """Verifica se a atividade está encerrada (prazo expirado)"""
        if not self.prazo_entrega:
            return False
        return timezone.now() > self.prazo_entrega
    
    def total_visualizacoes(self):
        """Retorna total de alunos que visualizaram"""
        return AtividadeVisualizacao.objects.filter(atividade=self).count()
    
    def total_envios(self):
        """Retorna total de alunos que enviaram"""
        return AtividadeEnvio.objects.filter(atividade=self).count()


class AtividadeVisualizacao(models.Model):
    """
    Controle de visualizações únicas por aluno
    """
    atividade = models.ForeignKey(
        Atividade, 
        on_delete=models.CASCADE, 
        related_name='visualizacoes_atividade',
        verbose_name='Atividade'
    )
    aluno = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'aluno'},
        verbose_name='Aluno'
    )
    visualizado_em = models.DateTimeField(auto_now_add=True, verbose_name='Visualizado em')
    
    class Meta:
        unique_together = ('atividade', 'aluno')
        verbose_name = 'Visualização de Atividade'
        verbose_name_plural = 'Visualizações de Atividades'
        ordering = ['-visualizado_em']
    
    def __str__(self):
        return f"{self.aluno.username} visualizou {self.atividade.titulo}"


class AtividadeEnvio(models.Model):
    """
    Envio de respostas de atividades por alunos
    """
    
    STATUS_CHOICES = [
        ('ENVIADA', 'Enviada'),
        ('CORRIGIDA', 'Corrigida'),
    ]
    
    atividade = models.ForeignKey(
        Atividade, 
        on_delete=models.CASCADE, 
        related_name='envios',
        verbose_name='Atividade'
    )
    aluno = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'aluno'},
        verbose_name='Aluno'
    )
    
    arquivo = models.FileField(
        upload_to='atividades_envios/',
        validators=[validate_file_size_atividade, validate_file_extension_atividade],
        verbose_name='Arquivo'
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='ENVIADA',
        verbose_name='Status'
    )
    
    enviado_em = models.DateTimeField(auto_now_add=True, verbose_name='Enviado em')
    
    # Campos opcionais para correção (futuro)
    nota = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='Nota'
    )
    feedback = models.TextField(blank=True, verbose_name='Feedback do Professor')
    
    class Meta:
        unique_together = ('atividade', 'aluno')
        verbose_name = 'Envio de Atividade'
        verbose_name_plural = 'Envios de Atividades'
        ordering = ['-enviado_em']
    
    def __str__(self):
        return f"{self.aluno.username} - {self.atividade.titulo}"


class AtividadeSalva(models.Model):
    """
    Atividades salvas pelo aluno para acesso rápido
    """
    aluno = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'aluno'},
        verbose_name='Aluno'
    )
    atividade = models.ForeignKey(
        Atividade, 
        on_delete=models.CASCADE,
        verbose_name='Atividade'
    )
    salva_em = models.DateTimeField(auto_now_add=True, verbose_name='Salva em')
    
    class Meta:
        unique_together = ('aluno', 'atividade')
        verbose_name = 'Atividade Salva'
        verbose_name_plural = 'Atividades Salvas'
        ordering = ['-salva_em']
    
    def __str__(self):
        return f"{self.aluno.username} salvou {self.atividade.titulo}"