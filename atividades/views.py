from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, F
from .models import Atividade, AtividadeVisualizacao, AtividadeEnvio, AtividadeSalva
from .forms import AtividadeForm, AtividadeEnvioForm
import os
import mimetypes


def is_professor(user):
    """Verifica se usuário é professor"""
    return user.is_authenticated and (user.user_type == 'professor' or user.is_staff)


def is_aluno(user):
    """Verifica se usuário é aluno"""
    return user.is_authenticated and user.user_type == 'aluno'


@login_required
def lista_atividades(request):
    """
    Lista de atividades - REDIRECIONA PROFESSOR PARA PAINEL
    """
    # Se for professor, redirecionar para painel
    if is_professor(request.user):
        return redirect('atividades:painel_professor')
    
    # Se não for aluno nem professor, erro
    if not is_aluno(request.user):
        messages.error(request, 'Acesso restrito.')
        return redirect('study:home')
    
    # Buscar atividades destinadas ao usuário
    atividades = Atividade.objects.all().order_by('-criado_em')
    
    # Filtros
    filtro_tipo = request.GET.get('tipo', '')
    filtro_status = request.GET.get('status', '')
    
    if filtro_tipo:
        atividades = atividades.filter(tipo=filtro_tipo)
    
    # Separar atividades por status
    if filtro_status == 'abertas':
        # Atividades não enviadas ou sem prazo
        atividades = atividades.exclude(
            envios__aluno=request.user
        ).filter(
            Q(prazo_entrega__gte=timezone.now()) | Q(prazo_entrega__isnull=True)
        )
    elif filtro_status == 'enviadas':
        # Atividades já enviadas
        atividades = atividades.filter(envios__aluno=request.user)
    elif filtro_status == 'pendentes':
        # Atividades não enviadas COM prazo
        atividades = atividades.exclude(
            envios__aluno=request.user
        ).filter(
            prazo_entrega__isnull=False
        )
    
    # Anotar status de cada atividade para o aluno
    atividades_anotadas = []
    for atividade in atividades:
        # Verificar se visualizou
        visualizou = AtividadeVisualizacao.objects.filter(
            atividade=atividade, 
            aluno=request.user
        ).exists()
        
        # Verificar se enviou
        envio = AtividadeEnvio.objects.filter(
            atividade=atividade, 
            aluno=request.user
        ).first()
        
        # Verificar se salvou
        salvou = AtividadeSalva.objects.filter(
            atividade=atividade,
            aluno=request.user
        ).exists()
        
        atividades_anotadas.append({
            'atividade': atividade,
            'visualizou': visualizou,
            'envio': envio,
            'salvou': salvou,
        })
    
    context = {
        'atividades_anotadas': atividades_anotadas,
        'filtro_tipo': filtro_tipo,
        'filtro_status': filtro_status,
    }
    
    return render(request, 'atividades/lista_aluno.html', context)


@login_required
def detalhe_atividade(request, pk):
    """
    Detalhe de atividade para aluno
    """
    if not is_aluno(request.user):
        messages.error(request, 'Acesso restrito a alunos.')
        return redirect('study:home')
    
    atividade = get_object_or_404(Atividade, pk=pk)
    
    # Registrar visualização (única)
    visualizacao, created = AtividadeVisualizacao.objects.get_or_create(
        atividade=atividade,
        aluno=request.user
    )
    
    if created:
        # Incrementar contador
        Atividade.objects.filter(pk=pk).update(visualizacoes=F('visualizacoes') + 1)
        
        # Marcar como visualizado
        if not atividade.foi_visualizado:
            atividade.foi_visualizado = True
            atividade.save(update_fields=['foi_visualizado'])
        
        atividade.refresh_from_db()
    
    # Verificar se já enviou
    envio = AtividadeEnvio.objects.filter(
        atividade=atividade,
        aluno=request.user
    ).first()
    
    # Verificar se salvou
    salvou = AtividadeSalva.objects.filter(
        atividade=atividade,
        aluno=request.user
    ).exists()
    
    context = {
        'atividade': atividade,
        'envio': envio,
        'salvou': salvou,
    }
    
    return render(request, 'atividades/detalhe_aluno.html', context)


@login_required
@require_POST
def enviar_atividade(request, pk):
    """
    Envio de atividade por aluno
    """
    if not is_aluno(request.user):
        return JsonResponse({'success': False, 'error': 'Acesso negado'}, status=403)
    
    atividade = get_object_or_404(Atividade, pk=pk)
    
    # Validar se permite envio
    if not atividade.permite_envio:
        return JsonResponse({
            'success': False, 
            'error': 'Esta atividade não permite envio.'
        }, status=400)
    
    # Validar prazo
    if atividade.esta_encerrada():
        return JsonResponse({
            'success': False, 
            'error': 'O prazo de entrega expirou.'
        }, status=400)
    
    # Verificar se já enviou
    if AtividadeEnvio.objects.filter(atividade=atividade, aluno=request.user).exists():
        return JsonResponse({
            'success': False, 
            'error': 'Você já enviou esta atividade.'
        }, status=400)
    
    form = AtividadeEnvioForm(request.POST, request.FILES)
    
    if form.is_valid():
        envio = form.save(commit=False)
        envio.atividade = atividade
        envio.aluno = request.user
        envio.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Atividade enviada com sucesso!'
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'Arquivo inválido ou muito grande (máx 10MB).'
        }, status=400)


@login_required
@require_POST
def salvar_atividade(request, pk):
    """
    Salvar atividade para acesso rápido
    """
    if not is_aluno(request.user):
        return JsonResponse({'success': False, 'error': 'Acesso negado'}, status=403)
    
    atividade = get_object_or_404(Atividade, pk=pk)
    
    salva, created = AtividadeSalva.objects.get_or_create(
        aluno=request.user,
        atividade=atividade
    )
    
    if created:
        return JsonResponse({
            'success': True,
            'action': 'saved',
            'message': 'Atividade salva!'
        })
    else:
        salva.delete()
        return JsonResponse({
            'success': True,
            'action': 'unsaved',
            'message': 'Atividade removida dos salvos.'
        })


@login_required
def baixar_anexo(request, pk):
    """
    Download do anexo da atividade
    """
    atividade = get_object_or_404(Atividade, pk=pk)
    
    if not atividade.anexo:
        raise Http404('Anexo não encontrado')
    
    file_path = atividade.anexo.path
    
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
def gerar_ics(request, pk):
    """
    Gerar arquivo .ics para agendamento
    """
    atividade = get_object_or_404(Atividade, pk=pk)
    
    if not atividade.prazo_entrega:
        messages.error(request, 'Esta atividade não possui prazo.')
        return redirect('atividades:detalhe', pk=pk)
    
    # Gerar conteúdo .ics
    from datetime import timedelta
    
    dtstart = atividade.prazo_entrega.strftime('%Y%m%dT%H%M%S')
    dtend = (atividade.prazo_entrega + timedelta(hours=1)).strftime('%Y%m%dT%H%M%S')
    
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//StudyMate//Atividades//PT
BEGIN:VEVENT
UID:{atividade.pk}@studymate.com
DTSTAMP:{timezone.now().strftime('%Y%m%dT%H%M%SZ')}
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:{atividade.titulo}
DESCRIPTION:{atividade.descricao or 'Atividade acadêmica'}
LOCATION:ETEC João Maria Stevanatto
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
    
    from django.http import HttpResponse
    response = HttpResponse(ics_content, content_type='text/calendar')
    response['Content-Disposition'] = f'attachment; filename="{atividade.titulo}.ics"'
    
    return response


# ========================================
# VIEWS PARA PROFESSORES
# ========================================

@login_required
@user_passes_test(is_professor)
def painel_professor(request):
    """
    Painel de controle do professor
    """
    atividades = Atividade.objects.filter(professor=request.user).order_by('-criado_em')
    
    # Anotar estatísticas
    atividades_anotadas = []
    for atividade in atividades:
        atividades_anotadas.append({
            'atividade': atividade,
            'total_visualizacoes': atividade.total_visualizacoes(),
            'total_envios': atividade.total_envios(),
        })
    
    context = {
        'atividades_anotadas': atividades_anotadas,
    }
    
    return render(request, 'atividades/painel_professor.html', context)


@login_required
@user_passes_test(is_professor)
def criar_atividade(request):
    """
    Criação de atividade por professor
    """
    if request.method == 'POST':
        form = AtividadeForm(request.POST, request.FILES)
        
        if form.is_valid():
            atividade = form.save(commit=False)
            atividade.professor = request.user
            atividade.save()
            
            messages.success(request, 'Atividade criada com sucesso!')
            return redirect('atividades:painel_professor')
    else:
        form = AtividadeForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'atividades/criar_atividade.html', context)


@login_required
@user_passes_test(is_professor)
def ver_envios(request, pk):
    """
    Visualizar envios de uma atividade
    """
    atividade = get_object_or_404(Atividade, pk=pk, professor=request.user)
    
    envios = AtividadeEnvio.objects.filter(atividade=atividade).order_by('-enviado_em')
    
    context = {
        'atividade': atividade,
        'envios': envios,
    }
    
    return render(request, 'atividades/ver_envios.html', context)


@login_required
@user_passes_test(is_professor)
def baixar_envio(request, pk):
    """
    Download de envio de aluno
    """
    envio = get_object_or_404(AtividadeEnvio, pk=pk, atividade__professor=request.user)
    
    if not envio.arquivo:
        raise Http404('Arquivo não encontrado')
    
    file_path = envio.arquivo.path
    
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
@user_passes_test(is_professor)
def excluir_atividade(request, pk):
    """
    Excluir atividade
    """
    atividade = get_object_or_404(Atividade, pk=pk, professor=request.user)
    
    if request.method == 'POST':
        atividade.delete()
        messages.success(request, 'Atividade excluída com sucesso!')
        return redirect('atividades:painel_professor')
    
    return render(request, 'atividades/confirmar_exclusao.html', {'atividade': atividade})