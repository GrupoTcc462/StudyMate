from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
import os
import re

User = get_user_model()


def validate_file_size_chat(file):
    """Valida o tamanho do arquivo (máx 10MB)"""
    max_size = 10 * 1024 * 1024  # 10MB
    if file.size > max_size:
        raise ValidationError(f'O arquivo não pode ser maior que 10MB')


def validate_file_extension_chat(file):
    """Valida a extensão do arquivo"""
    allowed = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.zip']
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed:
        raise ValidationError(f'Extensão {ext} não permitida. Use: {", ".join(allowed)}')


class Chat(models.Model):
    """
    Modelo para armazenar conversas entre usuários
    """
    remetente = models.ForeignKey(
        User, 
        related_name="chats_enviados", 
        on_delete=models.CASCADE,
        verbose_name='Remetente'
    )
    destinatario = models.ForeignKey(
        User, 
        related_name="chats_recebidos", 
        on_delete=models.CASCADE,
        verbose_name='Destinatário'
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    
    class Meta:
        verbose_name = 'Chat'
        verbose_name_plural = 'Chats'
        ordering = ['-data_criacao']
        unique_together = ('remetente', 'destinatario')
    
    def __str__(self):
        return f"Chat: {self.remetente.username} ↔ {self.destinatario.username}"
    
    def get_ultima_mensagem(self):
        """Retorna a última mensagem do chat"""
        return self.mensagens.order_by('-data_envio').first()
    
    def get_mensagens_nao_lidas(self, usuario):
        """Retorna quantidade de mensagens não lidas para um usuário"""
        return self.mensagens.filter(
            remetente=self.get_outro_usuario(usuario),
            lida=False
        ).count()
    
    def get_outro_usuario(self, usuario):
        """Retorna o outro usuário do chat"""
        if self.remetente == usuario:
            return self.destinatario
        return self.remetente


class Mensagem(models.Model):
    """
    Modelo para armazenar mensagens trocadas em um chat
    """
    chat = models.ForeignKey(
        Chat, 
        related_name="mensagens", 
        on_delete=models.CASCADE,
        verbose_name='Chat'
    )
    remetente = models.ForeignKey(
        User, 
        related_name="mensagens_enviadas", 
        on_delete=models.CASCADE,
        verbose_name='Remetente'
    )
    mensagem = models.TextField(verbose_name='Mensagem')
    anexo = models.FileField(
        upload_to='chat_anexos/',
        null=True,
        blank=True,
        validators=[validate_file_size_chat, validate_file_extension_chat],
        verbose_name='Anexo'
    )
    data_envio = models.DateTimeField(auto_now_add=True, verbose_name='Enviado em')
    lida = models.BooleanField(default=False, verbose_name='Lida')
    data_leitura = models.DateTimeField(null=True, blank=True, verbose_name='Lida em')
    
    class Meta:
        verbose_name = 'Mensagem'
        verbose_name_plural = 'Mensagens'
        ordering = ['data_envio']
    
    def __str__(self):
        return f"{self.remetente.username}: {self.mensagem[:50]}"
    
    def marcar_como_lida(self):
        """Marca mensagem como lida"""
        if not self.lida:
            self.lida = True
            self.data_leitura = timezone.now()
            self.save(update_fields=['lida', 'data_leitura'])
    
    def clean_message(self):
        """Remove palavras ofensivas da mensagem"""
        palavras_proibidas = [
            'faca', 'facada', 'matar', 'morrer', 'droga', 'cocaina',
            'maconha', 'crack', 'merda', 'porra', 'caralho', 'puta',
            'viado', 'bicha', 'otario', 'idiota', 'burro', 'imbecil', 'burro', 'Burro',
        ]
        
        mensagem_limpa = self.mensagem
        for palavra in palavras_proibidas:
            # Usar regex para buscar palavra completa (case insensitive)
            pattern = re.compile(r'\b' + re.escape(palavra) + r'\b', re.IGNORECASE)
            if pattern.search(mensagem_limpa):
                # Substituir por asteriscos do mesmo tamanho
                mensagem_limpa = pattern.sub('*' * len(palavra), mensagem_limpa)
        
        self.mensagem = mensagem_limpa
    
    def save(self, *args, **kwargs):
        # Limpar mensagem antes de salvar
        self.clean_message()
        super().save(*args, **kwargs)


class MensagemApagada(models.Model):
    """
    Controla mensagens apagadas por usuário (apenas localmente)
    """
    mensagem = models.ForeignKey(
        Mensagem, 
        on_delete=models.CASCADE,
        verbose_name='Mensagem'
    )
    usuario = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        verbose_name='Usuário'
    )
    data_apagada = models.DateTimeField(auto_now_add=True, verbose_name='Apagada em')
    
    class Meta:
        verbose_name = 'Mensagem Apagada'
        verbose_name_plural = 'Mensagens Apagadas'
        unique_together = ('mensagem', 'usuario')
    
    def __str__(self):
        return f"{self.usuario.username} apagou mensagem {self.mensagem.id}"