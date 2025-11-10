from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Sum
from django.utils import timezone
import json
from perfil.models import PerfilUsuario
from notes.models import Note, NoteLike, NoteRecommendation


@login_required
def perfil_view(request):
    """
    View principal do perfil com todas as estatísticas
    """
    user = request.user
    
    # Obter ou criar perfil
    perfil, created = PerfilUsuario.objects.get_or_create(user=user)
    
    # Atualizar streak quando acessar perfil
    perfil.update_streak()
    
    # Estatísticas de notes
    notes_count = Note.objects.filter(author=user).count()
    likes_count = NoteLike.objects.filter(user=user).count()
    
    # Downloads: somar todos os downloads dos notes do usuário
    downloads_count = Note.objects.filter(author=user).aggregate(
        total=Sum('downloads')
    )['total'] or 0
    
    # Se for professor: contar notes recomendados
    recommended_notes_count = 0
    if user.user_type == 'professor' or user.is_staff:
        recommended_notes_count = NoteRecommendation.objects.filter(teacher=user).count()
    
    context = {
        'streak_count': perfil.streak_count,
        'streak_progress': perfil.streak_progress(),
        'notes_count': notes_count,
        'likes_count': likes_count,
        'downloads_count': downloads_count,
        'recommended_notes_count': recommended_notes_count,
    }
    
    return render(request, 'perfil/perfil.html', context)


@login_required
@require_POST
def editar_nome(request):
    """
    View para editar nome do usuário (máximo 1 vez a cada 7 dias)
    """
    try:
        data = json.loads(request.body)
        new_name = data.get('name', '').strip()
        
        if not new_name:
            return JsonResponse({
                'success': False,
                'message': 'O nome não pode ficar em branco.'
            }, status=400)
        
        # Obter ou criar perfil
        perfil, created = PerfilUsuario.objects.get_or_create(user=request.user)
        
        # Verificar se pode alterar nome
        if not perfil.pode_alterar_nome():
            dias_restantes = perfil.dias_ate_proxima_mudanca()
            return JsonResponse({
                'success': False,
                'wait_days': dias_restantes,
                'message': f'Você só pode alterar o nome novamente em {dias_restantes} dia(s).'
            }, status=403)
        
        # Salvar nome antigo para retornar na resposta
        old_name = request.user.username
        
        # Atualizar nome
        request.user.username = new_name
        request.user.save()
        
        # Atualizar data da última mudança
        perfil.last_name_change = timezone.now()
        perfil.save()
        
        return JsonResponse({
            'success': True,
            'old_name': old_name,
            'new_name': new_name,
            'message': 'Nome alterado com sucesso!'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Dados inválidos.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao alterar nome: {str(e)}'
        }, status=500)