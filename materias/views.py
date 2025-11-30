from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Subject, LinkExterno


@login_required(login_url='/accounts/login/')
def materias_home(request):
    """
    Lista todas as matérias em ordem alfabética
    """
    materias = Subject.objects.all().order_by("name")
    context = {"materias": materias}
    return render(request, "materias/materias_list.html", context)


@login_required(login_url='/accounts/login/')
def get_links_materia(request, slug):
    """
    Retorna os links externos de uma matéria em JSON
    Para ser usado via AJAX no popup
    """
    materia = get_object_or_404(Subject, slug=slug)
    
    links = LinkExterno.objects.filter(
        materia=materia,
        ativo=True
    ).order_by('ordem', 'nome_site')
    
    links_data = [
        {
            'id': link.id,
            'nome': link.nome_site,
            'url': link.url,
            'descricao': link.descricao,
        }
        for link in links
    ]
    
    return JsonResponse({
        'materia': materia.name,
        'links': links_data,
    })