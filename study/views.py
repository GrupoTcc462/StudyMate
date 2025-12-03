from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.views.decorators.http import require_http_methods
from materias.models import Subject, LinkExterno
from notes.models import Note
from accounts.models import User
from django.utils import timezone
from datetime import timedelta


def home(request):
    """
    Página inicial do StudyMate
    """
    return render(request, 'study/home.html')


@require_http_methods(["GET"])
def stats_api(request):
    """
    API para retornar estatísticas em tempo real:
    - Matérias cadastradas
    - Notes criados
    - Alunos online (últimos 5 minutos)
    
    Endpoint: /study/api/stats/
    """
    try:
        # ========================================
        # 1. MATÉRIAS CADASTRADAS
        # ========================================
        materias_count = Subject.objects.count()
        
        # ========================================
        # 2. NOTES COMPARTILHADOS
        # ========================================
        notes_count = Note.objects.count()
        
        # ========================================
        # 3. ALUNOS ONLINE (últimos 5 minutos)
        # ========================================
        tempo_limite = timezone.now() - timedelta(minutes=5)
        
        alunos_online = User.objects.filter(
            user_type='aluno',
            last_login__gte=tempo_limite
        ).values('id', 'username', 'last_login').order_by('-last_login')
        
        alunos_online_count = alunos_online.count()
        
        # Converter para lista com formatação de data
        alunos_online_list = []
        for aluno in alunos_online:
            alunos_online_list.append({
                'id': aluno['id'],
                'username': aluno['username'],
                'last_login': aluno['last_login'].isoformat() if aluno['last_login'] else None
            })
        
        # ========================================
        # RETORNAR JSON
        # ========================================
        return JsonResponse({
            'success': True,
            'materias_count': materias_count,
            'notes_count': notes_count,
            'alunos_online_count': alunos_online_count,
            'alunos_online': alunos_online_list
        })
        
    except Exception as e:
        print(f"[ERRO] stats_api: {e}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def ping_api(request):
    """
    Endpoint opcional para atualizar last_login do usuário em tempo real.
    Chamado periodicamente pelo frontend via AJAX.
    
    Endpoint: /study/api/ping/
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Usuário não autenticado'
        }, status=401)
    
    try:
        # Atualizar last_login
        User.objects.filter(pk=request.user.pk).update(
            last_login=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Activity updated'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)