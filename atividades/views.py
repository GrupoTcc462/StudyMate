from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseForbidden, FileResponse, Http404, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import Atividade, AtividadeVisualizacao, AtividadeEnvio, AtividadeSalva
from .forms import AtividadeForm, AtividadeEnvioForm
import os
import mimetypes
import re


def is_professor(user):
    """Verifica se usuário é professor"""
    return user.is_authenticated and (user.user_type == 'professor' or user.is_staff)


def is_aluno(user):
    """Verifica se usuário é aluno"""
    return user.is_authenticated and user.user_type == 'aluno'


@login_required
def lista_atividades(request):
    """
    Lista de atividades - SISTEMA DE FILTROS TOTALMENTE RECONSTRUÍDO
    Funciona para: ALUNO, PROFESSOR e ADMINISTRADOR
    """
    user = request.user
    
    # ========================================
    # PROFESSORES: SUAS PRÓPRIAS ATIVIDADES
    # ========================================
    if is_professor(user):
        if request.method == 'POST':
            return processar_criacao_atividade(request)
        
        atividades = Atividade.objects.filter(professor=user)
    
    # ========================================
    # ALUNOS: ATIVIDADES DISPONÍVEIS
    # ========================================
    elif is_aluno(user):
        atividades = Atividade.objects.all()
    
    # ========================================
    # ADMINISTRADORES: TODAS AS ATIVIDADES
    # ========================================
    else:
        atividades = Atividade.objects.all()
    
    # ========================================
    # SISTEMA DE FILTROS (IGUAL AO NOTES)
    # ========================================
    filtro_tipo = request.GET.get('tipo', '')
    filtro_status = request.GET.get('status', '')
    filtro_order = request.GET.get('order', 'recent')
    
    # FILTRO 1: TIPO
    if filtro_tipo:
        atividades = atividades.filter(tipo=filtro_tipo)
    
    # FILTRO 2: STATUS (apenas para alunos)
    if is_aluno(user):
        if filtro_status == 'pendentes':
            # Atividades não enviadas e dentro do prazo
            atividades = atividades.exclude(
                envios__aluno=user
            ).filter(
                Q(prazo_entrega__gte=timezone.now()) | Q(prazo_entrega__isnull=True)
            )
        
        elif filtro_status == 'enviadas':
            # Atividades já enviadas pelo aluno
            atividades = atividades.filter(envios__aluno=user)
        
        elif filtro_status == 'abertas':
            # Atividades em aberto (não enviadas)
            atividades = atividades.exclude(envios__aluno=user)
    
    # FILTRO 3: ORDENAÇÃO
    order_map = {
        'recent': '-criado_em',
        'views': '-visualizacoes',
        'deadline': 'prazo_entrega',
        'saved': None  # Tratado separadamente
    }
    
    if filtro_order == 'saved' and is_aluno(user):
        # Apenas atividades salvas pelo aluno
        atividades_salvas_ids = AtividadeSalva.objects.filter(
            aluno=user
        ).values_list('atividade_id', flat=True)
        
        atividades = atividades.filter(id__in=atividades_salvas_ids).order_by('-criado_em')
    
    elif filtro_order in order_map and order_map[filtro_order]:
        atividades = atividades.order_by(order_map[filtro_order])
    
    else:
        atividades = atividades.order_by('-criado_em')
    
    # ========================================
    # ANOTAR INFORMAÇÕES ADICIONAIS
    # ========================================
    atividades_anotadas = []
    
    for atividade in atividades:
        item = {
            'atividade': atividade,
            'visualizou': False,
            'envio': None,
            'salvou': False,
        }
        
        # Informações específicas para alunos
        if is_aluno(user):
            item['visualizou'] = AtividadeVisualizacao.objects.filter(
                atividade=atividade, 
                aluno=user
            ).exists()
            
            item['envio'] = AtividadeEnvio.objects.filter(
                atividade=atividade, 
                aluno=user
            ).first()
            
            item['salvou'] = AtividadeSalva.objects.filter(
                atividade=atividade,
                aluno=user
            ).exists()
        
        atividades_anotadas.append(item)
    
    # ========================================
    # VERIFICAR SE HÁ RESULTADOS
    # ========================================
    tem_filtros_ativos = any([filtro_tipo, filtro_status, filtro_order != 'recent'])
    
    context = {
        'atividades_anotadas': atividades_anotadas,
        'filtro_tipo': filtro_tipo,
        'filtro_status': filtro_status,
        'filtro_order': filtro_order,
        'tem_filtros_ativos': tem_filtros_ativos,
        'total_atividades': len(atividades_anotadas),
    }
    
    return render(request, 'atividades/lista_aluno.html', context)


def processar_criacao_atividade(request):
    """
    Processa criação de atividade via modal
    """
    try:
        titulo = request.POST.get('titulo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        tipo = request.POST.get('tipo', '')
        
        ano_1 = 'ano_1' in request.POST
        ano_2 = 'ano_2' in request.POST
        ano_3 = 'ano_3' in request.POST
        todos = 'todos' in request.POST
        
        prazo_entrega = request.POST.get('prazo_entrega', '').strip()
        anexo = request.FILES.get('anexo')
        
        # VALIDAÇÕES
        if not titulo:
            messages.error(request, '❌ O título é obrigatório.')
            return redirect('atividades:lista')
            
        if len(titulo) > 50:
            messages.error(request, '❌ Título muito longo (máx 50 caracteres).')
            return redirect('atividades:lista')
        
        titulo_regex = r'^[A-Za-zÀ-ÿÇç\s]+$'
        if not re.match(titulo_regex, titulo):
            messages.error(request, '❌ Título contém caracteres não permitidos.')
            return redirect('atividades:lista')
        
        if not descricao:
            messages.error(request, '❌ A descrição é obrigatória.')
            return redirect('atividades:lista')
        
        if not any([ano_1, ano_2, ano_3, todos]):
            messages.error(request, '❌ Selecione pelo menos um ano.')
            return redirect('atividades:lista')
        
        if tipo not in ['ATIVIDADE', 'AVISO_PROVA', 'AVISO_SIMPLES']:
            messages.error(request, '❌ Tipo de atividade inválido.')
            return redirect('atividades:lista')
        
        # CRIAR ATIVIDADE
        atividade = Atividade(
            professor=request.user,
            titulo=titulo,
            descricao=descricao,
            tipo=tipo,
            ano_1=ano_1,
            ano_2=ano_2,
            ano_3=ano_3,
            todos=todos
        )
        
        # PRAZO
        if prazo_entrega:
            from django.utils.dateparse import parse_datetime
            prazo_dt = parse_datetime(prazo_entrega)
            
            if prazo_dt:
                if timezone.is_naive(prazo_dt):
                    prazo_dt = timezone.make_aware(prazo_dt)
                
                limite_minimo = timezone.now() + timedelta(minutes=30)
                
                if prazo_dt < limite_minimo:
                    messages.error(request, '❌ Prazo deve ser no mínimo 30 minutos.')
                    return redirect('atividades:lista')
                
                atividade.prazo_entrega = prazo_dt
        
        if anexo:
            atividade.anexo = anexo
        
        if tipo in ['AVISO_PROVA', 'AVISO_SIMPLES']:
            atividade.permite_envio = False
        
        atividade.save()
        
        anos_destino = atividade.get_anos_destino_display()
        messages.success(request, f'✅ Atividade "{titulo}" criada para: {anos_destino}.')
        
        return redirect('atividades:lista')
        
    except Exception as e:
        messages.error(request, f'❌ Erro ao criar atividade: {str(e)}')
        return redirect('atividades:lista')


@login_required
def detalhe_atividade(request, pk):
    """
    Detalhe de atividade
    """
    try:
        atividade = get_object_or_404(Atividade, pk=pk)
    except Atividade.DoesNotExist:
        messages.error(request, '❌ Atividade não encontrada. Pode ter sido excluída.')
        return redirect('atividades:lista')
    
    tem_acesso = False
    
    if atividade.professor == request.user:
        tem_acesso = True
    
    if request.user.user_type == 'aluno':
        tem_acesso = True
    
    if not tem_acesso:
        messages.error(request, 'Você não tem acesso a esta atividade.')
        return redirect('atividades:lista')
    
    # Registrar visualização
    if request.user.user_type == 'aluno':
        visualizacao, created = AtividadeVisualizacao.objects.get_or_create(
            atividade=atividade,
            aluno=request.user
        )
        
        if created:
            Atividade.objects.filter(pk=pk).update(visualizacoes=F('visualizacoes') + 1)
            
            if not atividade.foi_visualizado:
                atividade.foi_visualizado = True
                atividade.save(update_fields=['foi_visualizado'])
            
            atividade.refresh_from_db()
    
    envio = AtividadeEnvio.objects.filter(
        atividade=atividade,
        aluno=request.user
    ).first()
    
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
    
    if not atividade.permite_envio:
        return JsonResponse({
            'success': False, 
            'error': 'Esta atividade não permite envio.'
        }, status=400)
    
    if atividade.esta_encerrada():
        return JsonResponse({
            'success': False, 
            'error': 'O prazo de entrega expirou.'
        }, status=400)
    
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
    Salvar/remover atividade dos salvos
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
    
    response = HttpResponse(ics_content, content_type='text/calendar')
    response['Content-Disposition'] = f'attachment; filename="{atividade.titulo}.ics"'
    
    return response


# VIEWS PARA PROFESSORES

@login_required
@user_passes_test(is_professor)
def painel_professor(request):
    """
    Painel de controle do professor
    """
    atividades = Atividade.objects.filter(professor=request.user).order_by('-criado_em')
    
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
        return processar_criacao_atividade(request)
    
    return render(request, 'atividades/criar_atividade.html')


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