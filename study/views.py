from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta
from materias.models import Subject
from notes.models import Note
from accounts.models import User


def home(request):
    """
    Página inicial do StudyMate
    """
    return render(request, 'study/home.html')


# ========================================
# API PRINCIPAL - TODAS AS ESTATÍSTICAS
# ========================================
@require_http_methods(["GET"])
def stats_api(request):
    """
    Retorna TODAS as estatísticas de uma vez
    Endpoint: /study/api/stats/
    """
    try:
        # Matérias cadastradas
        materias_count = Subject.objects.count()
        
        # Notes compartilhados
        notes_count = Note.objects.count()
        
        # Alunos online (últimos 5 minutos)
        tempo_limite = timezone.now() - timedelta(minutes=5)
        
        alunos_online = User.objects.filter(
            user_type='aluno',
            last_login__gte=tempo_limite
        ).values('id', 'username', 'last_login').order_by('-last_login')
        
        alunos_online_count = alunos_online.count()
        
        # Converter para lista
        alunos_online_list = []
        for aluno in alunos_online:
            alunos_online_list.append({
                'id': aluno['id'],
                'username': aluno['username'],
                'last_login': aluno['last_login'].isoformat() if aluno['last_login'] else None
            })
        
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


# ========================================
# API INDIVIDUAL - MATÉRIAS
# ========================================
@require_http_methods(["GET"])
def materias_count_api(request):
    """
    Retorna apenas a contagem de matérias
    Endpoint: /study/api/materias_count/
    """
    try:
        count = Subject.objects.count()
        
        return JsonResponse({
            'success': True,
            'count': count,
            'message': 'Nenhuma matéria cadastrada' if count == 0 else f'{count} matéria(s) disponível(is)'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ========================================
# API INDIVIDUAL - NOTES
# ========================================
@require_http_methods(["GET"])
def notes_count_api(request):
    """
    Retorna apenas a contagem de notes
    Endpoint: /study/api/notes_count/
    """
    try:
        count = Note.objects.count()
        
        return JsonResponse({
            'success': True,
            'count': count,
            'message': 'Nenhum note criado' if count == 0 else f'{count} note(s) compartilhado(s)'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ========================================
# API INDIVIDUAL - ALUNOS ONLINE
# ========================================
@require_http_methods(["GET"])
def online_students_api(request):
    """
    Retorna lista completa de alunos online
    Endpoint: /study/api/online_students/
    """
    try:
        # Considerar online se fez login nos últimos 5 minutos
        tempo_limite = timezone.now() - timedelta(minutes=5)
        
        alunos_online = User.objects.filter(
            user_type='aluno',
            last_login__gte=tempo_limite
        ).values('id', 'username', 'email', 'last_login').order_by('-last_login')
        
        # Converter para lista com dados formatados
        alunos_list = []
        for aluno in alunos_online:
            last_login = aluno['last_login']
            agora = timezone.now()
            
            if last_login:
                diff = (agora - last_login).total_seconds()
                minutos = int(diff // 60)
                
                if minutos == 0:
                    tempo_texto = 'Agora'
                elif minutos == 1:
                    tempo_texto = '1 minuto atrás'
                else:
                    tempo_texto = f'{minutos} minutos atrás'
            else:
                tempo_texto = 'Desconhecido'
            
            alunos_list.append({
                'id': aluno['id'],
                'username': aluno['username'],
                'email': aluno['email'],
                'last_login': last_login.isoformat() if last_login else None,
                'tempo_texto': tempo_texto
            })
        
        return JsonResponse({
            'success': True,
            'count': len(alunos_list),
            'students': alunos_list,
            'message': 'Nenhum estudante online' if len(alunos_list) == 0 else f'{len(alunos_list)} estudante(s) online'
        })
        
    except Exception as e:
        print(f"[ERRO] online_students_api: {e}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)