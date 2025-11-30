from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Subject(models.Model):
    """Matéria (ex: Matemática, História)"""
    name = models.CharField(max_length=120, unique=True, verbose_name='Nome')
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True, verbose_name='Descrição')
    icone = models.CharField(max_length=10, blank=True, verbose_name='Ícone (emoji)', 
                              help_text='Ex: 📐, 📚, 🧪')

    class Meta:
        ordering = ['name']
        verbose_name = 'Matéria'
        verbose_name_plural = 'Matérias'

    def __str__(self):
        return self.name


class LinkExterno(models.Model):
    """
    Links para sites educacionais externos
    Admins cadastram até 5 links por matéria
    """
    materia = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='links_externos')
    nome_site = models.CharField(max_length=100, verbose_name='Nome do Site')
    url = models.URLField(verbose_name='URL Completo')
    descricao = models.CharField(max_length=200, blank=True, verbose_name='Descrição')
    ordem = models.IntegerField(default=0, verbose_name='Ordem de Exibição')
    adicionado_por = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    adicionado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        ordering = ['materia', 'ordem', 'nome_site']
        verbose_name = 'Link Externo'
        verbose_name_plural = 'Links Externos'

    def __str__(self):
        return f"{self.materia.name} - {self.nome_site}"