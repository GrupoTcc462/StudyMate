from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class PerfilUsuario(models.Model):
    """
    Modelo estendido para armazenar informações adicionais do perfil
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    last_name_change = models.DateTimeField(null=True, blank=True, verbose_name='Última alteração de nome')
    
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