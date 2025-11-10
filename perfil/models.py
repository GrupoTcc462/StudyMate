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
    last_name_change = models.DateTimeField(null=True, blank=True, verbose_name='Última alteração de nome')
    
    # ========================================
    # SISTEMA DE FREQUÊNCIA (LOGIN STREAK)
    # ========================================
    last_login_date = models.DateField(null=True, blank=True, verbose_name='Último login')
    streak_count = models.IntegerField(default=0, verbose_name='Dias consecutivos')
    
    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'
    
    def __str__(self):
        return f"Perfil de {self.user.username}"
    
    def pode_alterar_nome(self):
        """Verifica se passaram 7 dias desde a última alteração"""
        if not self.last_name_change:
            return True
        
        diff = (timezone.now() - self.last_name_change).days
        return diff >= 7
    
    def dias_ate_proxima_mudanca(self):
        """Retorna quantos dias faltam para poder alterar novamente"""
        if not self.last_name_change:
            return 0
        
        diff = (timezone.now() - self.last_name_change).days
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
            # Já fez login hoje, não faz nada
            return
        
        if self.last_login_date == today - timedelta(days=1):
            # Login consecutivo: incrementa
            self.streak_count += 1
        else:
            # Quebrou a sequência: reseta para 1
            self.streak_count = 1
        
        self.last_login_date = today
        self.save(update_fields=['last_login_date', 'streak_count'])
    
    def streak_progress(self):
        """
        Retorna progresso visual do streak (0-100%)
        Meta: 30 dias = 100%
        """
        return min((self.streak_count / 30) * 100, 100)