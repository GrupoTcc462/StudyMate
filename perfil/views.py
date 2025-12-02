from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.db.models import Sum, Count
from django.utils import timezone
from django.contrib.auth import authenticate
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
    
    # ========================================
    # ESTATÍSTICAS BÁSICAS
    # ========================================
    
    # Notes criados pelo usuário
    notes_count = Note.objects.filter(author=user).count()
    
    # Curtidas dadas pelo usuário
    likes_count = NoteLike.objects.filter(user=user).count()
    
    # Downloads totais recebidos nos notes do usuário
    downloads_count = Note.objects.filter(author=user).aggregate(
        total=Sum('downloads')
    )['total'] or 0
    
    # Recomendações (professores)
    recommended_notes_count = 0
    if user.user_type == 'professor' or user.is_staff:
        recommended_notes_count = NoteRecommendation.objects.filter(teacher=user).count()
    
    # ========================================
    # TEXTO DA OFENSIVA (CORRIGIDO)
    # ========================================
    dias_ofensiva = perfil.streak_count
    if dias_ofensiva == 1:
        texto_ofensiva = "1 dia seguido"
    else:
        texto_ofensiva = f"{dias_ofensiva} dias seguidos"
    
    context = {
        'streak_count': perfil.streak_count,
        'texto_ofensiva': texto_ofensiva,
        'streak_progress': perfil.streak_progress(),
        'notes_count': notes_count,
        'likes_count': likes_count,
        'downloads_count': downloads_count,
        'recommended_notes_count': recommended_notes_count,
    }
    
    return render(request, 'perfil/perfil.html', context)


@login_required
@require_http_methods(["GET"])
def popup_data(request, tipo):
    """
    Retorna dados atualizados para os popups em tempo real
    """
    user = request.user
    items = []
    
    try:
        if tipo == 'notes-criados':
            notes = Note.objects.filter(author=user).select_related('subject_new').order_by('-created_at')
            
            for note in notes:
                items.append({
                    'id': note.pk,
                    'title': note.title,
                    'subject': note.subject_new.nome if note.subject_new else 'Sem matéria',
                    'file_type': note.get_file_type_display(),
                    'created_at': note.created_at.strftime('%d/%m/%Y'),
                    'url': f'/notes/{note.pk}/'
                })
        
        elif tipo == 'curtidas-recebidas':
            notes = Note.objects.filter(author=user).order_by('-likes', '-views', '-downloads')
            
            for note in notes:
                items.append({
                    'id': note.pk,
                    'title': note.title,
                    'created_at': note.created_at.strftime('%d/%m/%Y'),
                    'likes': note.likes,
                    'views': note.views,
                    'downloads': note.downloads,
                    'comments_count': note.comments.count(),
                    'url': f'/notes/{note.pk}/'
                })
        
        elif tipo == 'downloads':
            # Sistema de rastreamento ainda não implementado
            pass
        
        elif tipo == 'recomendacoes':
            if user.user_type == 'professor' or user.is_staff:
                recomendacoes = NoteRecommendation.objects.filter(
                    teacher=user
                ).select_related('note', 'note__subject_new').order_by('-recommended_at')
                
                for rec in recomendacoes:
                    try:
                        items.append({
                            'id': rec.note.pk,
                            'title': rec.note.title,
                            'views': rec.note.views,
                            'likes': rec.note.likes,
                            'downloads': rec.note.downloads,
                            'recommended_at': rec.recommended_at.strftime('%d/%m/%Y às %H:%M'),
                            'url': f'/notes/{rec.note.pk}/'
                        })
                    except:
                        # Note foi deletado
                        pass
        
        return JsonResponse({
            'success': True,
            'items': items
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def check_password(request):
    """
    Verifica senha atual em tempo real
    """
    try:
        data = json.loads(request.body)
        password = data.get('password', '')
        
        # Autenticar usuário
        user = authenticate(username=request.user.username, password=password)
        
        return JsonResponse({'ok': user is not None})
        
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def editar_perfil(request):
    """
    Edita perfil do usuário (com restrição de 7 dias)
    """
    try:
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        current_password = request.POST.get('current_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        new_password_confirm = request.POST.get('new_password_confirm', '').strip()
        photo = request.FILES.get('photo')
        
        user = request.user
        perfil, created = PerfilUsuario.objects.get_or_create(user=user)
        
        # Verificar se pode editar (7 dias)
        if not perfil.pode_editar():
            return JsonResponse({
                'success': False,
                'error': f'Você só pode editar o perfil novamente em {perfil.dias_ate_proxima_edicao()} dia(s).'
            }, status=403)
        
        # Validar nome (apenas letras e espaços)
        if name:
            import re
            if not re.match(r'^[A-Za-zÀ-ÿÇç\s]+$', name):
                return JsonResponse({
                    'success': False,
                    'error': 'O nome só pode conter letras e espaços.'
                }, status=400)
            user.username = name
        
        # Validar e-mail
        if email and email != user.email:
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            try:
                validate_email(email)
                user.email = email
            except ValidationError:
                return JsonResponse({
                    'success': False,
                    'error': 'Formato de e-mail inválido.'
                }, status=400)
        
        # Alterar senha (se fornecida)
        if new_password:
            # Verificar senha atual
            if not authenticate(username=user.username, password=current_password):
                return JsonResponse({
                    'success': False,
                    'error': 'Senha atual incorreta.'
                }, status=400)
            
            # Verificar confirmação
            if new_password != new_password_confirm:
                return JsonResponse({
                    'success': False,
                    'error': 'As senhas não conferem.'
                }, status=400)
            
            # Validar força da senha
            import re
            if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&]).{8,}$', new_password):
                return JsonResponse({
                    'success': False,
                    'error': 'A senha não atende aos requisitos mínimos.'
                }, status=400)
            
            user.set_password(new_password)
        
        # Alterar foto
        new_photo_url = None
        if photo:
            perfil.photo = photo
            perfil.save()
            new_photo_url = perfil.photo.url
        
        # Salvar alterações
        user.save()
        
        # Atualizar timestamp de última edição
        perfil.last_edit = timezone.now()
        perfil.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Perfil atualizado com sucesso!',
            'new_photo_url': new_photo_url
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao atualizar perfil: {str(e)}'
        }, status=500)