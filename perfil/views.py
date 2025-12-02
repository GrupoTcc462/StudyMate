from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.contrib.auth import authenticate
from django.urls import reverse
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
    
    # Curtidas RECEBIDAS nos notes do usuário
    likes_count = NoteLike.objects.filter(note__author=user).count()
    
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
    Retorna dados atualizados para os popups em tempo real.
    CADA POPUP FUNCIONA DE FORMA INDEPENDENTE!
    """
    user = request.user
    items = []
    
    try:
        # ========================================
        # POPUP 1: NOTES CRIADOS
        # Mostra TODOS os notes criados pelo usuário
        # ========================================
        if tipo == 'notes-criados':
            notes = Note.objects.filter(
                author=user
            ).select_related('subject_new').order_by('-created_at')
            
            for note in notes:
                try:
                    items.append({
                        'id': note.pk,
                        'title': note.title,
                        'subject': note.subject_new.nome if note.subject_new else 'Sem matéria',
                        'file_type': note.get_file_type_display(),
                        'created_at': note.created_at.strftime('%d/%m/%Y'),
                        'url': reverse('notes:detail', args=[note.pk])
                    })
                except Exception as e:
                    print(f"Erro ao processar note {note.pk}: {e}")
                    continue
        
        # ========================================
        # POPUP 2: CURTIDAS RECEBIDAS
        # Mostra TODOS os notes que RECEBERAM curtidas
        # (INDEPENDENTE de terem sido recomendados ou não)
        # ========================================
        elif tipo == 'curtidas-recebidas':
            # Buscar notes do usuário que têm PELO MENOS 1 curtida
            notes = Note.objects.filter(
                author=user,
                likes__gt=0
            ).annotate(
                comments_count=Count('comments')
            ).order_by('-likes', '-views', '-downloads')
            
            for note in notes:
                try:
                    items.append({
                        'id': note.pk,
                        'title': note.title,
                        'created_at': note.created_at.strftime('%d/%m/%Y'),
                        'likes': note.likes,
                        'views': note.views,
                        'downloads': note.downloads,
                        'comments_count': note.comments_count,
                        'url': reverse('notes:detail', args=[note.pk])
                    })
                except Exception as e:
                    print(f"Erro ao processar note {note.pk}: {e}")
                    continue
        
        # ========================================
        # POPUP 3: DOWNLOADS
        # Mostra notes que FORAM BAIXADOS (downloads > 0)
        # (INDEPENDENTE de terem curtidas ou recomendações)
        # ========================================
        elif tipo == 'downloads':
            # Buscar notes do usuário que foram baixados
            notes_downloaded = Note.objects.filter(
                author=user,
                downloads__gt=0
            ).select_related('subject_new').order_by('-downloads', '-created_at')
            
            for note in notes_downloaded:
                try:
                    items.append({
                        'id': note.pk,
                        'title': note.title,
                        'tipo': 'Note',
                        'subject': note.subject_new.nome if note.subject_new else 'Sem matéria',
                        'downloads': note.downloads,
                        'likes': note.likes,
                        'views': note.views,
                        'created_at': note.created_at.strftime('%d/%m/%Y'),
                        'url': reverse('notes:detail', args=[note.pk])
                    })
                except Exception as e:
                    print(f"Erro ao processar note {note.pk}: {e}")
                    continue
            
            # TODO: Adicionar atividades e horários quando implementado
            # atividades = Atividade.objects.filter(downloads__gt=0)
            # horarios = Horario.objects.filter(downloads__gt=0)
        
        # ========================================
        # POPUP 4: RECOMENDAÇÕES (APENAS PROFESSORES)
        # Mostra notes que FORAM RECOMENDADOS pelo professor
        # (INDEPENDENTE de terem curtidas ou downloads)
        # ========================================
        elif tipo == 'recomendacoes':
            if user.user_type != 'professor' and not user.is_staff:
                return JsonResponse({
                    'success': False,
                    'error': 'Apenas professores podem ver recomendações.'
                }, status=403)
            
            # Buscar todas as recomendações feitas pelo professor
            recomendacoes = NoteRecommendation.objects.filter(
                teacher=user
            ).select_related('note', 'note__subject_new').order_by('-recommended_at')
            
            for rec in recomendacoes:
                try:
                    # Verificar se o note ainda existe
                    if rec.note:
                        items.append({
                            'id': rec.note.pk,
                            'title': rec.note.title,
                            'subject': rec.note.subject_new.nome if rec.note.subject_new else 'Sem matéria',
                            'views': rec.note.views,
                            'likes': rec.note.likes,
                            'downloads': rec.note.downloads,
                            'recommended_at': rec.recommended_at.strftime('%d/%m/%Y às %H:%M'),
                            'url': reverse('notes:detail', args=[rec.note.pk]),
                            'deleted': False
                        })
                    else:
                        # Note foi deletado
                        items.append({
                            'id': None,
                            'title': '❌ Note removido',
                            'subject': 'N/A',
                            'views': 0,
                            'likes': 0,
                            'downloads': 0,
                            'recommended_at': rec.recommended_at.strftime('%d/%m/%Y às %H:%M'),
                            'url': '#',
                            'deleted': True
                        })
                except Exception as e:
                    print(f"Erro ao processar recomendação {rec.pk}: {e}")
                    continue
        
        else:
            return JsonResponse({
                'success': False,
                'error': f'Tipo de popup inválido: {tipo}'
            }, status=400)
        
        # Log de debug
        print(f"[POPUP {tipo}] Retornando {len(items)} itens para usuário {user.username}")
        
        return JsonResponse({
            'success': True,
            'items': items,
            'total': len(items)
        })
        
    except Exception as e:
        print(f"[ERRO CRÍTICO] popup_data ({tipo}): {e}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'error': f'Erro ao carregar dados: {str(e)}'
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
    # ========================================
# ADICIONAR ESTAS VIEWS NO ARQUIVO perfil/views.py
# ========================================

@login_required
@require_http_methods(["POST"])
def check_username(request):
    """
    Verifica se um nome de usuário está disponível
    """
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        current_username = data.get('current_username', '')
        
        # Se for o mesmo usuário atual, está disponível
        if username.lower() == current_username.lower():
            return JsonResponse({'available': True})
        
        # Verificar se existe outro usuário com esse nome
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        exists = User.objects.filter(username__iexact=username).exists()
        
        return JsonResponse({'available': not exists})
        
    except Exception as e:
        return JsonResponse({'available': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def check_email(request):
    """
    Verifica se um e-mail está disponível
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        current_email = data.get('current_email', '').lower()
        
        # Se for o mesmo e-mail atual, está disponível
        if email == current_email:
            return JsonResponse({'available': True})
        
        # Verificar se existe outro usuário com esse e-mail
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        exists = User.objects.filter(email__iexact=email).exists()
        
        return JsonResponse({'available': not exists})
        
    except Exception as e:
        return JsonResponse({'available': False, 'error': str(e)})