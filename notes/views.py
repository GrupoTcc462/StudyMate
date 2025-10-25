from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden, FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.db import IntegrityError
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Note, Comment, NoteLike, Subject, NoteView, NoteRecommendation
from .utils import user_is_professor, get_professor_subject
import mimetypes
import os


def notes_list(request):
    """Lista de notes com filtros e paginação"""
    qs = Note.objects.select_related('author', 'subject').prefetch_related('comments', 'recommendations')
    
    # Filtros
    subject_slug = request.GET.get('subject', '')
    file_type = request.GET.get('file_type', '')
    order = request.GET.get('order', 'recent')
    show_recommended = request.GET.get('recommended', '')
    
    if subject_slug:
        qs = qs.filter(subject__slug=subject_slug)
    
    if file_type:
        qs = qs.filter(file_type=file_type)
    
    if show_recommended:
        qs = qs.filter(recommendations__isnull=False).distinct()
    
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
    
    # Lista de matérias ativas para o filtro
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    
    # Verificar se usuário é professor
    is_professor = user_is_professor(request.user) if request.user.is_authenticated else False
    
    context = {
        'page_obj': page_obj,
        'subjects': subjects,
        'current_subject': subject_slug,
        'current_file_type': file_type,
        'current_order': order,
        'file_types': Note.FILE_TYPES,
        'user_is_professor': is_professor,
    }
    
    return render(request, 'notes/notes_list.html', context)


def note_detail(request, pk):
    """Detalhe de um note com incremento de views POR USUÁRIO"""
    note = get_object_or_404(Note.objects.select_related('author', 'subject'), pk=pk)
    
    cookie_name = f'viewed_note_{note.pk}'
    view_counted = False
    
    # 1) Usuário autenticado: registrar NoteView (uma vez por usuário)
    if request.user.is_authenticated:
        try:
            _, created = NoteView.objects.get_or_create(user=request.user, note=note)
            if created:
                Note.objects.filter(pk=note.pk).update(views=F('views') + 1)
                note.refresh_from_db(fields=['views'])
                view_counted = True
        except IntegrityError:
            # Já existe registro
            pass
    else:
        # 2) Usuário anônimo: usar cookie (fallback)
        if not request.COOKIES.get(cookie_name):
            Note.objects.filter(pk=note.pk).update(views=F('views') + 1)
            note.refresh_from_db(fields=['views'])
            view_counted = True
    
    # Verificar se usuário já curtiu
    user_liked = False
    if request.user.is_authenticated:
        user_liked = NoteLike.objects.filter(note=note, user=request.user).exists()
    
    # Processar comentário
    if request.method == 'POST' and request.user.is_authenticated:
        text = request.POST.get('text', '').strip()
        if text and len(text) <= 400:
            Comment.objects.create(note=note, author=request.user, text=text)
            messages.success(request, 'Comentário adicionado com sucesso!')
            return redirect('notes:detail', pk=pk)
        else:
            messages.error(request, 'Comentário inválido (máx 400 caracteres)')
    
    # Verificar se autor é professor
    is_author_teacher = user_is_professor(note.author)
    
    # Buscar recomendações
    recommendations = note.recommendations.select_related('professor', 'subject').all()
    recommendations_preview = recommendations[:2]  # Primeiros 2 para exibição
    
    # Verificar se usuário atual pode recomendar
    can_recommend = False
    if request.user.is_authenticated and user_is_professor(request.user):
        # Professor pode recomendar se a matéria do note corresponder à sua
        professor_subject = get_professor_subject(request.user)
        can_recommend = (professor_subject is None) or (note.subject == professor_subject)
    
    user_recommended = False
    if request.user.is_authenticated:
        user_recommended = note.recommendations.filter(professor=request.user).exists()
    
    comments = note.comments.select_related('author').all()
    
    context = {
        'note': note,
        'comments': comments,
        'user_liked': user_liked,
        'is_author_teacher': is_author_teacher,
        'recommendations': recommendations,
        'recommendations_preview': recommendations_preview,
        'recommendations_count': recommendations.count(),
        'can_recommend': can_recommend,
        'user_recommended': user_recommended,
    }
    
    # Preparar response
    response = render(request, 'notes/note_detail.html', context)
    
    # Setar cookie para anônimos se view foi contada
    if not request.user.is_authenticated and view_counted:
        response.set_cookie(
            cookie_name, 
            '1', 
            max_age=30*24*60*60,  # 30 dias
            httponly=True, 
            samesite='Lax'
        )
    
    return response


@login_required
@require_POST
def note_create(request):
    """Criação de note via POST (AJAX)"""
    try:
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        file_type = request.POST.get('file_type', '')
        subject_id = request.POST.get('subject', '').strip()
        file = request.FILES.get('file')
        link = request.POST.get('link', '').strip()
        
        # Validações básicas
        if not title or len(title) > 150:
            return JsonResponse({'success': False, 'error': 'Título inválido'}, status=400)
        
        if file_type not in dict(Note.FILE_TYPES):
            return JsonResponse({'success': False, 'error': 'Tipo inválido'}, status=400)
        
        # Buscar Subject
        subject = None
        if subject_id:
            subject = Subject.objects.filter(pk=subject_id, is_active=True).first()
        
        # Criar note
        note = Note(
            author=request.user,
            title=title,
            description=description,
            file_type=file_type,
            subject=subject
        )
        
        # Validar conteúdo conforme tipo
        if file_type == 'LINK':
            if not link:
                return JsonResponse({'success': False, 'error': 'Link obrigatório'}, status=400)
            note.link = link
        elif file_type == 'TXT':
            # Para texto, descrição serve como conteúdo
            if not description:
                return JsonResponse({'success': False, 'error': 'Descrição obrigatória para tipo TXT'}, status=400)
        else:
            # Outros tipos precisam de arquivo
            if not file:
                return JsonResponse({'success': False, 'error': 'Arquivo obrigatório'}, status=400)
            note.file = file
        
        # Permitir que professores marquem como recomendado ao criar
        if user_is_professor(request.user):
            is_recommended = request.POST.get('is_recommended') == 'true'
            note.is_recommended = is_recommended
        
        note.full_clean()  # Validações do model
        note.save()
        
        messages.success(request, 'Note criado com sucesso!')
        
        return JsonResponse({
            'success': True,
            'note': {
                'id': note.pk,
                'title': note.title,
                'url': f'/notes/{note.pk}/'
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def recommend_note(request, pk):
    """
    Recomendar/remover recomendação de um note
    Apenas professores podem recomendar
    Professor só pode recomendar notes da SUA matéria (se configurado)
    """
    if not user_is_professor(request.user):
        return JsonResponse({
            'success': False, 
            'error': 'Apenas professores podem recomendar notes'
        }, status=403)
    
    note = get_object_or_404(Note, pk=pk)
    
    # Verificar se professor pode recomendar esta matéria
    professor_subject = get_professor_subject(request.user)
    
    if professor_subject and note.subject and note.subject != professor_subject:
        return JsonResponse({
            'success': False,
            'error': f'Você só pode recomendar notes da matéria {professor_subject.name}'
        }, status=400)
    
    # Toggle recomendação
    rec, created = NoteRecommendation.objects.get_or_create(
        note=note,
        professor=request.user,
        defaults={'subject': note.subject}
    )
    
    if not created:
        # Já existe -> remover recomendação
        rec.delete()
        action = 'removed'
    else:
        action = 'added'
    
    # Retornar dados atualizados
    total = note.recommendations.count()
    recs_data = list(
        note.recommendations.select_related('professor', 'subject')
        .values('professor__username', 'subject__name', 'created_at')[:10]
    )
    
    return JsonResponse({
        'success': True,
        'action': action,
        'total': total,
        'recs': recs_data,
        'user_recommended': (action == 'added')
    })


@login_required
@require_POST
def like_note(request, pk):
    """Curtir/descurtir um note"""
    note = get_object_or_404(Note, pk=pk)
    
    like, created = NoteLike.objects.get_or_create(note=note, user=request.user)
    
    if created:
        # Like criado - incrementar contador
        Note.objects.filter(pk=pk).update(likes=F('likes') + 1)
        note.refresh_from_db(fields=['likes'])
        liked = True
    else:
        # Like já existe - remover (unlike)
        like.delete()
        Note.objects.filter(pk=pk).update(likes=F('likes') - 1)
        note.refresh_from_db(fields=['likes'])
        liked = False
    
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
    
    # Incrementar downloads atomicamente
    Note.objects.filter(pk=pk).update(downloads=F('downloads') + 1)
    
    # Servir arquivo
    file_path = note.file.path
    
    if not os.path.exists(file_path):
        raise Http404('Arquivo não encontrado no servidor')
    
    # Detectar tipo MIME
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'
    
    # Nome do arquivo original (sanitizado)
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
        return JsonResponse({'success': False, 'error': 'Comentário inválido'}, status=400)
    
    comment = Comment.objects.create(note=note, author=request.user, text=text)
    
    return JsonResponse({
        'success': True,
        'comment': {
            'author': comment.author.username,
            'text': comment.text,
            'created_at': comment.created_at.strftime('%d/%m/%Y %H:%M')
        }
    })