from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Modelo de usuário customizado com tipos de usuário
    """
    USER_TYPE_CHOICES = (
        ('admin', 'Administrador'),
        ('professor', 'Professor'),
        ('aluno', 'Aluno'),  # Atualizado de 'estudante' para 'aluno'
    )
    
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='aluno',  # Atualizado
        verbose_name='Tipo de Usuário'
    )
    
    # Campos adicionais opcionais
    matricula = models.CharField(max_length=20, blank=True, null=True, verbose_name='Matrícula')
    telefone = models.CharField(max_length=15, blank=True, null=True, verbose_name='Telefone')
    
    # Controle de primeiro login
    first_login = models.BooleanField(default=True, verbose_name='Primeiro Login')
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
    
    def __str__(self):
        return f"{self.username} - {self.get_user_type_display()}"
    
    def is_admin_user(self):
        return self.user_type == 'admin'
    
    def is_professor(self):
        return self.user_type == 'professor'
    
    def is_aluno(self):
        return self.user_type == 'aluno'