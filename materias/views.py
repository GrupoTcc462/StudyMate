from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Subject
from notes.models import Note


@login_required(login_url='/accounts/login/')
def materias_home(request):
    """Lista todas as matérias em ordem alfabética"""
    materias = Subject.objects.all().order_by("name")
    context = {"materias": materias}
    return render(request, "materias/materias_list.html", context)


@login_required(login_url='/accounts/login/')
def subject_detail(request, slug):
    """
    Detalhes da matéria com:
    - Botões de métodos de estudo
    - Barra de pesquisa que busca nas notes
    """
    materia = get_object_or_404(Subject, slug=slug)
    query = request.GET.get("q", "").strip()
    content_type = request.GET.get("type", "")
    
    notes = None
    
    # Se houver busca, filtra as notes da matéria
    if query:
        notes = Note.objects.filter(
            subject__iexact=materia.name  # Busca case-insensitive pela matéria
        ).filter(
            Q(title__icontains=query) |  # Busca no título
            Q(description__icontains=query)  # Busca na descrição
        ).select_related('author').order_by('-is_recommended', '-likes', '-views')
    
    # Filtro por tipo de conteúdo (quando clica nos botões)
    elif content_type:
        # Mapeia os tipos de Content para os tipos de Note
        type_mapping = {
            'vid': 'LINK',  # Vídeo-aulas geralmente são links
            'doc': 'PDF',   # PDFs e Docs
            'map': 'PDF',   # Mapas mentais em PDF
            'res': 'PDF',   # Resumos em PDF
            'exe': 'PDF',   # Listas de exercícios
        }
        
        note_type = type_mapping.get(content_type, 'PDF')
        notes = Note.objects.filter(
            subject__iexact=materia.name,
            file_type=note_type
        ).select_related('author').order_by('-is_recommended', '-likes', '-views')

    context = {
        "materia": materia,
        "query": query,
        "notes": notes,
        "content_type": content_type,
    }
    return render(request, "materias/subject_detail.html", context)