from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta

User = get_user_model()


class PerfilUsuario(models.Model):
    """
    Modelo estendido para armazenar informações adicionais do perfil
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    
    # FOTO DE PERFIL
    photo = models.ImageField(upload_to='profile_pics/', null=True, blank=True, verbose_name='Foto de Perfil')
    
    # CONTROLE DE EDIÇÕES (7 DIAS)
    last_edit = models.DateTimeField(null=True, blank=True, verbose_name='Última edição do perfil')
    
    # SISTEMA DE FREQUÊNCIA (LOGIN STREAK)
    last_login_date = models.DateField(null=True, blank=True, verbose_name='Último login')
    streak_count = models.IntegerField(default=0, verbose_name='Dias consecutivos')
    
    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'
    
    def __str__(self):
        return f"Perfil de {self.user.username}"
    
    def pode_editar(self):
        """
        Verifica se passaram 7 dias desde a última edição.
        Superusers podem editar sem restrição.
        """
        if self.user.is_superuser:
            return True
        
        if not self.last_edit:
            return True
        
        diff = (timezone.now() - self.last_edit).days
        return diff >= 7
    
    def dias_ate_proxima_edicao(self):
        """Retorna quantos dias faltam para poder editar novamente"""
        if self.user.is_superuser or not self.last_edit:
            return 0
        
        diff = (timezone.now() - self.last_edit).days
        return max(0, 7 - diff)
    
    def update_streak(self):
        """
        Atualiza o contador de dias consecutivos de login.
        
        Regras:
        - Se último login foi ontem: incrementa contador
        - Se último login foi hoje: não faz nada (já contou)
        - Se último login foi há mais de 1 dia: reseta para 1
        """
        today = date.today()
        
        if self.last_login_date == today:
            return
        
        if self.last_login_date == today - timedelta(days=1):
            self.streak_count += 1
        else:
            self.streak_count = 1
        
        self.last_login_date = today
        self.save(update_fields=['last_login_date', 'streak_count'])
    
    def streak_progress(self):
        """Retorna progresso visual do streak (0-100%). Meta: 30 dias = 100%"""
        return min((self.streak_count / 30) * 100, 100)