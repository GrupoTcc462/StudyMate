from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden, FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Note, Comment, NoteLike, NoteView, NoteRecommendation
import mimetypes
import os
import re


def notes_list(request):
    """Lista de notes com filtros e paginação"""
    qs = Note.objects.select_related('author').prefetch_related('comments')
    
    # Filtros
    subject = request.GET.get('subject', '')
    file_type = request.GET.get('file_type', '')
    order = request.GET.get('order', 'recent')
    recommended = request.GET.get('recommended', '')
    
    if subject:
        qs = qs.filter(subject__iexact=subject)
    
    if file_type:
        qs = qs.filter(file_type=file_type)
    
    if recommended == 'true':
        qs = qs.filter(is_recommended=True)
    
    # Ordenação
    ordering_map = {
        'recent': '-created_at',
        'likes': '-likes',
        'views': '-views',
        'downloads': '-downloads'
    }
    qs = qs.order_by(ordering_map.get(order, '-created_at'))
    
    # Paginação
    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Lista de matérias únicas para o filtro
    subjects = Note.objects.values_list('subject', flat=True).distinct().order_by('subject')
    subjects = [s for s in subjects if s]
    
    context = {
        'page_obj': page_obj,
        'subjects': subjects,
        'current_subject': subject,
        'current_file_type': file_type,
        'current_order': order,
        'file_types': Note.FILE_TYPES,
    }
    
    return render(request, 'notes/notes_list.html', context)


def note_detail(request, pk):
    """
    Detalhe de um note com incremento ÚNICO de views por usuário logado.
    Usuários não logados NÃO contam visualização.
    """
    note = get_object_or_404(Note.objects.select_related('author'), pk=pk)
    
    # ========================================
    # CONTROLE DE VISUALIZAÇÕES (APENAS USUÁRIOS LOGADOS)
    # ========================================
    if request.user.is_authenticated:
        # Criar visualização apenas se NÃO existir
        view_created = NoteView.objects.get_or_create(note=note, user=request.user)
        
        # Se foi criado agora (primeira vez), incrementar contador
        if view_created[1]:  # [1] é o boolean 'created'
            Note.objects.filter(pk=pk).update(views=F('views') + 1)
            note.refresh_from_db(fields=['views'])
    
    # Verificar se usuário já curtiu
    user_liked = False
    if request.user.is_authenticated:
        user_liked = NoteLike.objects.filter(note=note, user=request.user).exists()
    
    # ========================================
    # PROCESSAR COMENTÁRIO (APENAS LOGADOS)
    # ========================================
    if request.method == 'POST' and request.user.is_authenticated:
        text = request.POST.get('text', '').strip()
        
        # Validar caracteres permitidos e tamanho
        if text and len(text) <= 400 and validate_text_content(text):
            Comment.objects.create(note=note, author=request.user, text=text)
            messages.success(request, 'Comentário adicionado com sucesso!')
            return redirect('notes:detail', pk=pk)
        else:
            messages.error(request, 'Comentário inválido. Use apenas letras, espaços e pontuação básica (máx 400 caracteres)')
    
    # ========================================
    # SISTEMA DE RECOMENDAÇÕES
    # ========================================
    # Buscar recomendações de professores
    recommendations = NoteRecommendation.objects.filter(note=note).select_related('teacher')
    
    # Determinar qual recomendação exibir (prioridade: mesma matéria)
    primary_recommendation = None
    other_recommendations_count = 0
    
    if recommendations.exists():
        # Filtrar professores da mesma matéria do note (se houver matéria)
        if note.subject:
            same_subject_recs = [r for r in recommendations if hasattr(r.teacher, 'teacher_subjects') and note.subject in r.teacher.teacher_subjects]
            
            if same_subject_recs:
                primary_recommendation = same_subject_recs[0]
                other_recommendations_count = len(recommendations) - 1
            else:
                primary_recommendation = recommendations[0]
                other_recommendations_count = len(recommendations) - 1
        else:
            primary_recommendation = recommendations[0]
            other_recommendations_count = len(recommendations) - 1
    
    # Verificar recomendação automática (se não houver manual)
    auto_recommend_reason = None
    if note.is_recommended and not recommendations.exists():
        if note.downloads >= 20:
            auto_recommend_reason = "downloads"
        elif note.likes >= 40:
            auto_recommend_reason = "likes"
        elif note.views >= 50:
            auto_recommend_reason = "views"
    
    # Verificar se autor é professor
    is_author_teacher = note.author.user_type == 'professor' or note.author.is_staff
    
    # Verificar se usuário atual pode recomendar
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
    """
    Valida se o texto contém APENAS caracteres permitidos:
    - Letras (maiúsculas, minúsculas, acentuadas, cedilha)
    - Espaços
    - Pontuação básica (. , ! ? ; : - ( ) ' ")
    """
    pattern = r'^[a-zA-ZàáâãäåèéêëìíîïòóôõöùúûüýÿçÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÝŸÇ\s.,!?;:\-()\'\"]+$'
    return bool(re.match(pattern, text))


@login_required
@require_POST
def note_create(request):
    """Criação de note com TODAS as validações do relatório"""
    try:
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        file_type = request.POST.get('file_type', '')
        subject = request.POST.get('subject', '').strip()
        file = request.FILES.get('file')
        link = request.POST.get('link', '').strip()
        
        # ========================================
        # VALIDAÇÃO DO TÍTULO (50 caracteres, APENAS letras e espaços)
        # ========================================
        if not title or len(title) > 50:
            return JsonResponse({
                'success': False, 
                'error': 'Título inválido (máx 50 caracteres)'
            }, status=400)
        
        # Regex: APENAS letras (com acentos) e espaços
        title_regex = r'^[A-Za-zÀ-ÿÇç\s]+$'
        if not re.match(title_regex, title):
            return JsonResponse({
                'success': False, 
                'error': 'Título contém caracteres não permitidos. Use apenas letras e espaços.'
            }, status=400)
        
        # ========================================
        # VALIDAÇÃO DA DESCRIÇÃO (400 caracteres)
        # ========================================
        if description and len(description) > 400:
            return JsonResponse({
                'success': False, 
                'error': 'Descrição muito longa (máx 400 caracteres)'
            }, status=400)
        
        if description and not validate_text_content(description):
            return JsonResponse({
                'success': False, 
                'error': 'Descrição contém caracteres não permitidos.'
            }, status=400)
        
        # ========================================
        # VALIDAÇÃO DO TIPO DE CONTEÚDO
        # ========================================
        if file_type not in dict(Note.FILE_TYPES):
            return JsonResponse({
                'success': False, 
                'error': 'Tipo de conteúdo inválido'
            }, status=400)
        
        # Criar objeto Note
        note = Note(
            author=request.user,
            title=title,
            description=description,
            file_type=file_type,
            subject=subject if subject else None
        )
        
        # ========================================
        # VALIDAÇÃO DE CONTEÚDO POR TIPO
        # ========================================
        if file_type == 'LINK':
            if not link:
                return JsonResponse({
                    'success': False, 
                    'error': 'Link obrigatório para tipo Link Externo'
                }, status=400)
            
            url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
            if not re.match(url_pattern, link):
                return JsonResponse({
                    'success': False, 
                    'error': 'Link inválido. Use um URL completo (ex: https://exemplo.com)'
                }, status=400)
            
            note.link = link
        
        elif file_type == 'DOC':
            # WORD: permitir upload OU criação online
            if not file:
                return JsonResponse({
                    'success': False, 
                    'error': 'Arquivo obrigatório para tipo Word'
                }, status=400)
            
            file_ext = os.path.splitext(file.name)[1].lower()
            if file_ext not in ['.doc', '.docx']:
                return JsonResponse({
                    'success': False, 
                    'error': 'Formato inválido. Use .doc ou .docx'
                }, status=400)
            
            note.file = file
        
        else:
            # Outros tipos (PDF, PPT): precisam de arquivo
            if not file:
                return JsonResponse({
                    'success': False, 
                    'error': 'Arquivo obrigatório para este tipo de conteúdo'
                }, status=400)
            
            allowed_extensions = {
                'PDF': ['.pdf'],
                'PPT': ['.ppt', '.pptx']
            }
            
            file_ext = os.path.splitext(file.name)[1].lower()
            expected_exts = allowed_extensions.get(file_type, [])
            
            if file_ext not in expected_exts:
                return JsonResponse({
                    'success': False, 
                    'error': f'Formato não suportado. Use: {", ".join(expected_exts)}'
                }, status=400)
            
            note.file = file
        
        # Validar modelo completo
        note.full_clean()
        note.save()
        
        return JsonResponse({
            'success': True,
            'note': {
                'id': note.pk,
                'title': note.title,
                'url': f'/notes/{note.pk}/'
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': f'Erro ao criar note: {str(e)}'
        }, status=400)


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
    
    # Verificar recomendação automática
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
    
    # Incrementar downloads
    Note.objects.filter(pk=pk).update(downloads=F('downloads') + 1)
    note.refresh_from_db(fields=['downloads'])
    
    # Verificar recomendação automática
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
    """
    NOVA VIEW - Professores podem recomendar/remover recomendação de notes.
    """
    if not (request.user.user_type == 'professor' or request.user.is_staff):
        return JsonResponse({
            'success': False,
            'error': 'Apenas professores podem recomendar notes'
        }, status=403)
    
    note = get_object_or_404(Note, pk=pk)
    
    # Verificar se já recomendou
    recommendation = NoteRecommendation.objects.filter(note=note, teacher=request.user).first()
    
    if recommendation:
        # Remover recomendação
        recommendation.delete()
        
        # Se não houver mais recomendações manuais, desmarcar is_recommended
        if not NoteRecommendation.objects.filter(note=note).exists():
            note.is_recommended = False
            note.save(update_fields=['is_recommended'])
        
        return JsonResponse({
            'success': True,
            'recommended': False,
            'message': 'Recomendação removida'
        })
    else:
        # Adicionar recomendação
        NoteRecommendation.objects.create(note=note, teacher=request.user)
        note.is_recommended = True
        note.save(update_fields=['is_recommended'])
        
        return JsonResponse({
            'success': True,
            'recommended': True,
            'message': 'Note recomendado com sucesso'
        })