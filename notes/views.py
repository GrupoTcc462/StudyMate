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


def notes_list(request):
    """Lista de notes com filtros e paginação - CORRIGIDA"""
    
    # ========================================
    # QUERY BASE - SEMPRE MOSTRA TODOS OS NOTES
    # ========================================
    qs = Note.objects.select_related('author', 'subject_new').prefetch_related('comments')
    
    # Filtros opcionais
    subject = request.GET.get('subject', '')
    file_type = request.GET.get('file_type', '')
    order = request.GET.get('order', 'recent')
    recommended = request.GET.get('recommended', '')
    
    # ========================================
    # APLICAR FILTROS (se houver)
    # ========================================
    if subject:
        qs = qs.filter(subject_new__nome__iexact=subject)
    
    if file_type:
        qs = qs.filter(file_type=file_type)
    
    if recommended == 'true':
        qs = qs.filter(is_recommended=True)
    
    # ========================================
    # ORDENAÇÃO
    # ========================================
    ordering_map = {
        'recent': '-created_at',
        'likes': '-likes',
        'views': '-views',
        'downloads': '-downloads'
    }
    
    order_field = ordering_map.get(order, '-created_at')
    qs = qs.order_by(order_field)
    
    # ========================================
    # DEBUG: Verificar quantos notes existem
    # ========================================
    total_notes = qs.count()
    print(f"[DEBUG] Total de notes na query: {total_notes}")
    
    # ========================================
    # PAGINAÇÃO
    # ========================================
    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    print(f"[DEBUG] Notes na página atual: {page_obj.object_list.count()}")
    
    # ========================================
    # LISTA DE MATÉRIAS PARA FILTRO E MODAL
    # ========================================
    subjects_list = Materia.objects.all().order_by('nome')
    
    # ========================================
    # CONTEXTO
    # ========================================
    context = {
        'page_obj': page_obj,
        'subjects': subjects_list,
        'materias': subjects_list,  # Para o modal
        'current_subject': subject,
        'current_file_type': file_type,
        'current_order': order,
        'file_types': Note.FILE_TYPES,
        'total_notes': total_notes,  # Para debug
    }
    
    return render(request, 'notes/notes_list.html', context)


def note_detail(request, pk):
    """Detalhe de um note com incremento ÚNICO de views por usuário logado"""
    note = get_object_or_404(Note.objects.select_related('author', 'subject_new'), pk=pk)
    
    # Controle de visualizações
    if request.user.is_authenticated:
        view_created = NoteView.objects.get_or_create(note=note, user=request.user)
        
        if view_created[1]:
            Note.objects.filter(pk=pk).update(views=F('views') + 1)
            note.refresh_from_db(fields=['views'])
    
    user_liked = False
    if request.user.is_authenticated:
        user_liked = NoteLike.objects.filter(note=note, user=request.user).exists()
    
    # Processar comentário
    if request.method == 'POST' and request.user.is_authenticated:
        text = request.POST.get('text', '').strip()
        
        if text and len(text) <= 400 and validate_text_content(text):
            Comment.objects.create(note=note, author=request.user, text=text)
            messages.success(request, 'Comentário adicionado com sucesso!')
            return redirect('notes:detail', pk=pk)
        else:
            messages.error(request, 'Comentário inválido.')
    
    # Sistema de recomendações
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


@login_required
def note_create(request):
    """Criação de note - CORRIGIDO COM DEBUG"""
    if request.method != 'POST':
        return redirect('notes:list')
    
    try:
        # ========================================
        # LOG DE DEBUG
        # ========================================
        print("=" * 50)
        print("DEBUG NOTE CREATE")
        print(f"POST data: {request.POST}")
        print(f"FILES: {request.FILES}")
        print("=" * 50)
        
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        file_type = request.POST.get('file_type', '')
        subject_id = request.POST.get('subject', '').strip()
        file = request.FILES.get('file')
        link = request.POST.get('link', '').strip()
        
        # Validação do título
        if not title:
            messages.error(request, 'Título é obrigatório.')
            return redirect('notes:list')
        
        if len(title) > 50:
            messages.error(request, 'Título muito longo (máximo 50 caracteres).')
            return redirect('notes:list')
        
        title_regex = r'^[A-Za-zÀ-ÿÇç\s]+$'
        if not re.match(title_regex, title):
            messages.error(request, 'Título contém caracteres não permitidos. Use apenas letras e espaços.')
            return redirect('notes:list')
        
        # Validação da descrição
        if description and len(description) > 400:
            messages.error(request, 'Descrição muito longa (máximo 400 caracteres).')
            return redirect('notes:list')
        
        if description and not validate_text_content(description):
            messages.error(request, 'Descrição contém caracteres não permitidos.')
            return redirect('notes:list')
        
        # Validação do tipo de conteúdo
        valid_types = [code for code, _ in Note.FILE_TYPES]
        if file_type not in valid_types:
            messages.error(request, 'Tipo de conteúdo inválido.')
            return redirect('notes:list')
        
        # Validação da matéria
        materia = None
        if subject_id:
            try:
                materia = Materia.objects.get(id=subject_id)
                print(f"[DEBUG] Matéria selecionada: {materia.nome}")
            except (Materia.DoesNotExist, ValueError):
                messages.error(request, 'Matéria inválida.')
                return redirect('notes:list')
        
        # Criar objeto Note
        note = Note(
            author=request.user,
            title=title,
            description=description,
            file_type=file_type,
            subject_new=materia
        )
        
        # Validação por tipo de conteúdo
        if file_type == 'LINK':
            if not link:
                messages.error(request, 'Link é obrigatório para tipo Link Externo.')
                return redirect('notes:list')
            
            url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
            if not re.match(url_pattern, link):
                messages.error(request, 'Link inválido. Use um URL completo (ex: https://exemplo.com).')
                return redirect('notes:list')
            
            note.link = link
        
        elif file_type == 'DOC':
            if not file:
                messages.error(request, 'Arquivo é obrigatório para tipo Word.')
                return redirect('notes:list')
            
            file_ext = os.path.splitext(file.name)[1].lower()
            if file_ext not in ['.doc', '.docx']:
                messages.error(request, 'Formato inválido. Use .doc ou .docx.')
                return redirect('notes:list')
            
            if file.size > 10 * 1024 * 1024:
                messages.error(request, 'Arquivo muito grande (máximo 10MB).')
                return redirect('notes:list')
            
            note.file = file
        
        elif file_type == 'PDF':
            if not file:
                messages.error(request, 'Arquivo é obrigatório para tipo PDF.')
                return redirect('notes:list')
            
            file_ext = os.path.splitext(file.name)[1].lower()
            if file_ext != '.pdf':
                messages.error(request, 'Formato inválido. Use .pdf.')
                return redirect('notes:list')
            
            if file.size > 10 * 1024 * 1024:
                messages.error(request, 'Arquivo muito grande (máximo 10MB).')
                return redirect('notes:list')
            
            note.file = file
        
        elif file_type == 'PPT':
            if not file:
                messages.error(request, 'Arquivo é obrigatório para tipo Apresentação.')
                return redirect('notes:list')
            
            file_ext = os.path.splitext(file.name)[1].lower()
            if file_ext not in ['.ppt', '.pptx']:
                messages.error(request, 'Formato inválido. Use .ppt ou .pptx.')
                return redirect('notes:list')
            
            if file.size > 10 * 1024 * 1024:
                messages.error(request, 'Arquivo muito grande (máximo 10MB).')
                return redirect('notes:list')
            
            note.file = file
        
        # ========================================
        # SALVAR NOTE
        # ========================================
        note.full_clean()
        note.save()
        
        print(f"[DEBUG] Note criado com sucesso! ID: {note.pk}, Título: {note.title}")
        print(f"[DEBUG] Matéria: {note.subject_new.nome if note.subject_new else 'Nenhuma'}")
        
        messages.success(request, f'Note "{title}" criado com sucesso!')
        
        # ========================================
        # REDIRECIONAR PARA A LISTA (sem filtros)
        # ========================================
        return redirect('notes:list')
        
    except Exception as e:
        print(f"[ERRO] Ao criar note: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'Erro ao criar note: {str(e)}')
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