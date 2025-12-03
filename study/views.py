from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from materias.models import Subject, LinkExterno
from notes.models import Note
from accounts.models import User

def home(request):
    return render(request, 'study/home.html')


def stats_api(request):
    """
    API para retornar estatísticas em tempo real:
    - Links cadastrados (total de links ativos em todas as matérias)
    - Estudantes online (apenas alunos)
    - Notes compartilhados
    """
    
    # LINKS CADASTRADOS (total de links ATIVOS em todas as matérias)
    links_count = LinkExterno.objects.filter(ativo=True).count()
    
    # ESTUDANTES ONLINE (apenas user_type='aluno')
    # Considera online: usuários logados nos últimos 15 minutos
    from django.utils import timezone
    from datetime import timedelta
    
    tempo_limite = timezone.now() - timedelta(minutes=15)
    
    alunos_online = User.objects.filter(
        user_type='aluno',
        last_login__gte=tempo_limite
    ).values('id', 'username', 'last_login').order_by('-last_login')
    
    alunos_online_count = alunos_online.count()
    alunos_online_list = list(alunos_online)
    
    # NOTES COMPARTILHADOS
    notes_count = Note.objects.count()
    
    return JsonResponse({
        'success': True,
        'links_cadastrados': links_count,
        'estudantes_online': {
            'count': alunos_online_count,
            'alunos': alunos_online_list
        },
        'notes_compartilhados': notes_count
    })