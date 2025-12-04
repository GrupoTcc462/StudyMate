from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden, FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Materia, Note, Comment, NoteLike, NoteView, NoteRecommendation
import mimetypes
import os
import re
import json
import urllib.request
import urllib.error


def notes_list(request):
    """Lista de notes com filtros e paginação"""
    qs = Note.objects.select_related('author', 'subject_new').prefetch_related('comments')

    # Filtros
    subject = request.GET.get('subject', '')
    file_type = request.GET.get('file_type', '')
    order = request.GET.get('order', 'recent')
    recommended = request.GET.get('recommended', '')

    if subject:
        qs = qs.filter(subject_new_id=subject)

    if file_type:
        qs = qs.filter(file_type=file_type)

    if recommended == 'true':
        qs = qs.filter(is_recommended=True)

    ordering_map = {
        'recent': '-created_at',
        'likes': '-likes',
        'views': '-views',
        'downloads': '-downloads'
    }
    qs = qs.order_by(ordering_map.get(order, '-created_at'))

    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    materias = Materia.objects.all().order_by('nome')

    context = {
        'page_obj': page_obj,
        'materias': materias,
        'file_types': Note.FILE_TYPES,
        'current_subject': subject,
        'current_file_type': file_type,
        'current_order': order,
    }

    return render(request, 'notes/notes_list.html', context)


def note_detail(request, pk):
    """Detalhe de um note com incremento ÚNICO de views por usuário logado"""
    note = get_object_or_404(Note.objects.select_related('author', 'subject_new'), pk=pk)
    
    if request.user.is_authenticated:
        view_created = NoteView.objects.get_or_create(note=note, user=request.user)
        
        if view_created[1]:
            Note.objects.filter(pk=pk).update(views=F('views') + 1)
            note.refresh_from_db(fields=['views'])
    
    user_liked = False
    if request.user.is_authenticated:
        user_liked = NoteLike.objects.filter(note=note, user=request.user).exists()
    
    if request.method == 'POST' and request.user.is_authenticated:
        text = request.POST.get('text', '').strip()
        
        if text and len(text) <= 400 and validate_text_content(text):
            Comment.objects.create(note=note, author=request.user, text=text)
            messages.success(request, 'Comentário adicionado com sucesso!')
            return redirect('notes:detail', pk=pk)
        else:
            messages.error(request, 'Comentário inválido.')
    
    recommendations = NoteRecommendation.objects.filter(note=note).select_related('teacher')
    
    primary_recommendation = None
    other_recommendations_count = 0
    
    if recommendations.exists():
        primary_recommendation = recommendations[0]
        other_recommendations_count = len(recommendations) - 1
    
    auto_recommend_reason = None
    if note.is_recommended and not recommendations.exists():
        if note.downloads >= 20:
            auto_recommend_reason = "downloads"
        elif note.likes >= 40:
            auto_recommend_reason = "likes"
        elif note.views >= 50:
            auto_recommend_reason = "views"
    
    is_author_teacher = note.author.user_type == 'professor' or note.author.is_staff
    
    can_recommend = request.user.is_authenticated and (request.user.user_type == 'professor' or request.user.is_staff)
    user_has_recommended = False
    if can_recommend:
        user_has_recommended = NoteRecommendation.objects.filter(note=note, teacher=request.user).exists()
    
    comments = note.comments.select_related('author').all()
    
    context = {
        'note': note,
        'comments': comments,
        'user_liked': user_liked,
        'is_author_teacher': is_author_teacher,
        'can_recommend': can_recommend,
        'user_has_recommended': user_has_recommended,
        'primary_recommendation': primary_recommendation,
        'other_recommendations_count': other_recommendations_count,
        'all_recommendations': recommendations,
        'auto_recommend_reason': auto_recommend_reason,
    }
    
    return render(request, 'notes/note_detail.html', context)


def validate_text_content(text):
    """Valida se o texto contém APENAS caracteres permitidos"""
    pattern = r'^[a-zA-ZàáâãäåèéêëìíîïòóôõöùúûüýÿçÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÝŸÇ\s.,!?;:\-()\'\"]+$'
    return bool(re.match(pattern, text))


def validate_safe_url(url):
    """
    🔥 NOVA VALIDAÇÃO: Verifica se URL é segura (HTTPS)
    """
    if not url:
        return False, "URL vazia"
    
    # Verificar se começa com http:// ou https://
    if not (url.startswith('http://') or url.startswith('https://')):
        return False, "URL deve começar com http:// ou https://"
    
    # Verificar se é HTTPS (recomendado)
    is_https = url.startswith('https://')
    
    # Tentar acessar URL para verificar se existe
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                if is_https:
                    return True, "URL válida e segura (HTTPS)"
                else:
                    return True, "⚠️ URL válida mas não segura (HTTP). Recomendamos usar HTTPS."
    except urllib.error.HTTPError as e:
        return False, f"Erro HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"URL inacessível: {e.reason}"
    except Exception as e:
        return False, f"Erro ao verificar URL: {str(e)}"
    
    return False, "URL inválida"


@login_required
def note_create(request):
    """
    🔥 CRIAÇÃO DE NOTE COM TODAS AS VALIDAÇÕES
    """
    if request.method != 'POST':
        return redirect('notes:list')
    
    try:
        # ========================================
        # CAPTURA DE DADOS
        # ========================================
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        file_type = request.POST.get('file_type', '')
        subject_id = request.POST.get('subject', '').strip()
        file = request.FILES.get('file')
        link = request.POST.get('link', '').strip()
        
        # ========================================
        # 🔥 VALIDAÇÃO 1: TÍTULO OBRIGATÓRIO
        # ========================================
        if not title:
            messages.error(request, '❌ Título é obrigatório.')
            return redirect('notes:list')
        
        if len(title) > 50:
            messages.error(request, '❌ Título muito longo (máximo 50 caracteres).')
            return redirect('notes:list')
        
        title_regex = r'^[A-Za-zÀ-ÿÇç\s]+$'
        if not re.match(title_regex, title):
            messages.error(request, '❌ Título contém caracteres não permitidos. Use apenas letras e espaços.')
            return redirect('notes:list')
        
        # ========================================
        # 🔥 VALIDAÇÃO 2: DESCRIÇÃO
        # ========================================
        if description and len(description) > 400:
            messages.error(request, '❌ Descrição muito longa (máximo 400 caracteres).')
            return redirect('notes:list')
        
        if description and not validate_text_content(description):
            messages.error(request, '❌ Descrição contém caracteres não permitidos.')
            return redirect('notes:list')
        
        # ========================================
        # 🔥 VALIDAÇÃO 3: TIPO DE CONTEÚDO OBRIGATÓRIO
        # ========================================
        valid_types = [code for code, _ in Note.FILE_TYPES]
        if not file_type or file_type not in valid_types:
            messages.error(request, '❌ Tipo de conteúdo é obrigatório.')
            return redirect('notes:list')
        
        # ========================================
        # 🔥 VALIDAÇÃO 4: MATÉRIA OBRIGATÓRIA
        # ========================================
        materia = None
        if not subject_id:
            messages.error(request, '❌ Matéria é obrigatória.')
            return redirect('notes:list')
        
        try:
            subject_id = int(subject_id)
            materia = Materia.objects.get(id=subject_id)
        except (Materia.DoesNotExist, ValueError):
            messages.error(request, '❌ Matéria inválida.')
            return redirect('notes:list')
        
        # ========================================
        # 🔥 VALIDAÇÃO 5: ARQUIVO OU LINK OBRIGATÓRIO
        # ========================================
        note = Note(
            author=request.user,
            title=title,
            description=description,
            file_type=file_type,
            subject_new=materia
        )
        
        # TIPO: LINK
        if file_type == 'LINK':
            if not link:
                messages.error(request, '❌ Link é obrigatório para tipo Link Externo.')
                return redirect('notes:list')
            
            # 🔥 VALIDAÇÃO EXTRA: LINK SEGURO
            is_valid, message = validate_safe_url(link)
            
            if not is_valid:
                messages.error(request, f'❌ {message}')
                return redirect('notes:list')
            
            # Se for HTTP (não HTTPS), mostrar aviso mas permitir
            if link.startswith('http://'):
                messages.warning(request, '⚠️ Este link usa HTTP (não seguro). Recomendamos usar HTTPS quando possível.')
            
            note.link = link
        
        # TIPO: ARQUIVO (DOC, PDF, PPT)
        else:
            if not file:
                messages.error(request, '❌ Arquivo é obrigatório para este tipo de conteúdo.')
                return redirect('notes:list')
            
            # 🔥 VALIDAÇÃO 6: TAMANHO DO ARQUIVO (50MB)
            if file.size > 50 * 1024 * 1024:
                messages.error(request, '❌ O arquivo excede o limite de 50MB.')
                return redirect('notes:list')
            
            # 🔥 VALIDAÇÃO 7: EXTENSÃO DO ARQUIVO
            file_ext = os.path.splitext(file.name)[1].lower()
            
            allowed_extensions = {
                'DOC': ['.doc', '.docx'],
                'PDF': ['.pdf'],
                'PPT': ['.ppt', '.pptx']
            }
            
            if file_type in allowed_extensions:
                if file_ext not in allowed_extensions[file_type]:
                    messages.error(
                        request, 
                        f'❌ Formato inválido. Use: {", ".join(allowed_extensions[file_type])}'
                    )
                    return redirect('notes:list')
            
            note.file = file
        
        # ========================================
        # SALVAR NOTE
        # ========================================
        note.full_clean()  # Chama validações do model
        note.save()
        
        messages.success(request, f'✅ Note "{title}" criado com sucesso!')
        return redirect('notes:list')
        
    except Exception as e:
        print(f"[ERRO] ❌ Ao criar note: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'❌ Erro ao criar note: {str(e)}')
        return redirect('notes:list')


@login_required
@require_POST
def like_note(request, pk):
    """Curtir/descurtir um note"""
    note = get_object_or_404(Note, pk=pk)
    
    like, created = NoteLike.objects.get_or_create(note=note, user=request.user)
    
    if created:
        Note.objects.filter(pk=pk).update(likes=F('likes') + 1)
        note.refresh_from_db(fields=['likes'])
        liked = True
    else:
        like.delete()
        Note.objects.filter(pk=pk).update(likes=F('likes') - 1)
        note.refresh_from_db(fields=['likes'])
        liked = False
    
    note.check_auto_recommend()
    
    return JsonResponse({
        'success': True,
        'likes': note.likes,
        'liked': liked
    })


@login_required
def download_note(request, pk):
    """Download de arquivo com incremento de contador"""
    note = get_object_or_404(Note, pk=pk)
    
    if not note.file:
        raise Http404('Arquivo não encontrado')
    
    Note.objects.filter(pk=pk).update(downloads=F('downloads') + 1)
    note.refresh_from_db(fields=['downloads'])
    
    note.check_auto_recommend()
    
    file_path = note.file.path
    
    if not os.path.exists(file_path):
        raise Http404('Arquivo não encontrado no servidor')
    
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'
    
    filename = os.path.basename(file_path)
    
    response = FileResponse(open(file_path, 'rb'), content_type=mime_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
@require_POST
def add_comment(request, pk):
    """Adicionar comentário via AJAX"""
    note = get_object_or_404(Note, pk=pk)
    text = request.POST.get('text', '').strip()
    
    if not text or len(text) > 400:
        return JsonResponse({
            'success': False, 
            'error': 'Comentário inválido (máx 400 caracteres)'
        }, status=400)
    
    if not validate_text_content(text):
        return JsonResponse({
            'success': False, 
            'error': 'Comentário contém caracteres não permitidos'
        }, status=400)
    
    comment = Comment.objects.create(note=note, author=request.user, text=text)
    
    return JsonResponse({
        'success': True,
        'comment': {
            'author': comment.author.username,
            'text': comment.text,
            'created_at': comment.created_at.strftime('%d/%m/%Y %H:%M')
        }
    })


@login_required
@require_POST
def toggle_recommend(request, pk):
    """Professores podem recomendar/remover recomendação de notes"""
    if not (request.user.user_type == 'professor' or request.user.is_staff):
        return JsonResponse({
            'success': False,
            'error': 'Apenas professores podem recomendar notes'
        }, status=403)
    
    note = get_object_or_404(Note, pk=pk)
    
    recommendation = NoteRecommendation.objects.filter(note=note, teacher=request.user).first()
    
    if recommendation:
        recommendation.delete()
        
        if not NoteRecommendation.objects.filter(note=note).exists():
            note.is_recommended = False
            note.save(update_fields=['is_recommended'])
        
        return JsonResponse({
            'success': True,
            'recommended': False,
            'message': 'Recomendação removida'
        })
    else:
        NoteRecommendation.objects.create(note=note, teacher=request.user)
        note.is_recommended = True
        note.save(update_fields=['is_recommended'])
        
        return JsonResponse({
            'success': True,
            'recommended': True,
            'message': 'Note recomendado com sucesso'
        })