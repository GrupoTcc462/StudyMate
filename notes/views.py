from django.shortcuts import render

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden, FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Note, Comment, NoteLike
import mimetypes
import os


def notes_list(request):
    """Lista de notes com filtros e paginação"""
    qs = Note.objects.select_related('author').prefetch_related('comments')
    
    # Filtros
    subject = request.GET.get('subject', '')
    file_type = request.GET.get('file_type', '')
    order = request.GET.get('order', 'recent')
    
    if subject:
        qs = qs.filter(subject__iexact=subject)
    
    if file_type:
        qs = qs.filter(file_type=file_type)
    
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
    subjects = [s for s in subjects if s]  # Remove valores None
    
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
    """Detalhe de um note com incremento de views"""
    note = get_object_or_404(Note.objects.select_related('author'), pk=pk)
    
    # Incrementa views atomicamente
    Note.objects.filter(pk=pk).update(views=F('views') + 1)
    note.refresh_from_db(fields=['views'])
    
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
    is_author_teacher = note.author.user_type == 'professor' or note.author.is_staff
    
    comments = note.comments.select_related('author').all()
    
    context = {
        'note': note,
        'comments': comments,
        'user_liked': user_liked,
        'is_author_teacher': is_author_teacher,
    }
    
    return render(request, 'notes/note_detail.html', context)


@login_required
@require_POST
def note_create(request):
    """Criação de note via POST"""
    try:
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        file_type = request.POST.get('file_type', '')
        subject = request.POST.get('subject', '').strip()
        file = request.FILES.get('file')
        link = request.POST.get('link', '').strip()
        
        # Validações básicas
        if not title or len(title) > 150:
            return JsonResponse({'success': False, 'error': 'Título inválido'}, status=400)
        
        if file_type not in dict(Note.FILE_TYPES):
            return JsonResponse({'success': False, 'error': 'Tipo inválido'}, status=400)
        
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
        
        # Permitir que professores marquem como recomendado
        if request.user.user_type == 'professor' or request.user.is_staff:
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
    
    # Incrementar downloads
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
