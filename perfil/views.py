from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import json

from notes.models import Note, NoteLike, Comment
from .models import PerfilUsuario


@login_required
def perfil_view(request):
    """View principal da aba Perfil"""
    user = request.user
    
    # Criar perfil se não existir
    perfil, created = PerfilUsuario.objects.get_or_create(user=user)
    
    # Estatísticas do usuário
    notes_count = Note.objects.filter(author=user).count()
    likes_count = NoteLike.objects.filter(user=user).count()
    downloads_count = sum(Note.objects.filter(author=user).values_list('downloads', flat=True))
    comments_count = Comment.objects.filter(author=user).count()
    
    context = {
        'user': user,
        'perfil': perfil,
        'notes_count': notes_count,
        'likes_count': likes_count,
        'downloads_count': downloads_count,
        'comments_count': comments_count,
    }
    
    return render(request, 'perfil/perfil.html', context)


@login_required
@require_POST
def editar_nome(request):
    """Editar nome do usuário com restrição de 7 dias"""
    try:
        data = json.loads(request.body)
        new_name = data.get('name', '').strip()
        
        if not new_name:
            return JsonResponse({
                'success': False,
                'error': 'O nome não pode ficar em branco.'
            }, status=400)
        
        user = request.user
        perfil, created = PerfilUsuario.objects.get_or_create(user=user)
        
        # Verificar se pode alterar
        if not perfil.pode_alterar_nome():
            dias_restantes = perfil.dias_ate_proxima_mudanca()
            return JsonResponse({
                'success': False,
                'wait_days': dias_restantes,
                'message': f'Você só poderá alterar o nome novamente em {dias_restantes} dias.'
            })
        
        # Guardar nome antigo
        old_name = user.username
        
        # Atualizar nome
        user.username = new_name
        user.save()
        
        # Atualizar data da última mudança
        perfil.last_name_change = timezone.now()
        perfil.save()
        
        return JsonResponse({
            'success': True,
            'old_name': old_name,
            'new_name': new_name,
            'message': f'Nome alterado com sucesso! De {old_name} para {new_name}.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)