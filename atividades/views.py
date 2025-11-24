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
    Lista de atividades - CORRIGIDO: PROCESSA CRIAÇÃO VIA MODAL
    """
    # Se for professor, processar criação ou exibir suas atividades
    if is_professor(request.user):
        # PROCESSAR CRIAÇÃO DE ATIVIDADE VIA MODAL (POST)
        if request.method == 'POST':
            return processar_criacao_atividade(request)
        
        # Exibir lista com modal
        atividades = Atividade.objects.filter(professor=request.user).order_by('-criado_em')
        
        atividades_anotadas = []
        for atividade in atividades:
            atividades_anotadas.append({
                'atividade': atividade,
                'visualizou': False,
                'envio': None,
                'salvou': False,
            })
        
        context = {
            'atividades_anotadas': atividades_anotadas,
            'filtro_tipo': '',
            'filtro_status': '',
        }
        
        return render(request, 'atividades/lista_aluno.html', context)
    
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
        atividades = atividades.exclude(
            envios__aluno=request.user
        ).filter(
            Q(prazo_entrega__gte=timezone.now()) | Q(prazo_entrega__isnull=True)
        )
    elif filtro_status == 'enviadas':
        atividades = atividades.filter(envios__aluno=request.user)
    elif filtro_status == 'pendentes':
        atividades = atividades.exclude(
            envios__aluno=request.user
        ).filter(
            prazo_entrega__isnull=False
        )
    
    # Anotar status de cada atividade para o aluno
    atividades_anotadas = []
    for atividade in atividades:
        visualizou = AtividadeVisualizacao.objects.filter(
            atividade=atividade, 
            aluno=request.user
        ).exists()
        
        envio = AtividadeEnvio.objects.filter(
            atividade=atividade, 
            aluno=request.user
        ).first()
        
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


def processar_criacao_atividade(request):
    """
    FUNÇÃO CORRIGIDA - Processa criação de atividade via modal
    """
    try:
        # Capturar dados do POST
        titulo = request.POST.get('titulo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        tipo = request.POST.get('tipo', '')
        
        # CORRIGIDO: Capturar checkboxes
        # Quando checkbox está marcado, vem como 'on' no POST
        ano_1 = 'ano_1' in request.POST
        ano_2 = 'ano_2' in request.POST
        ano_3 = 'ano_3' in request.POST
        todos = 'todos' in request.POST
        
        prazo_entrega = request.POST.get('prazo_entrega', '').strip()
        anexo = request.FILES.get('anexo')
        
        # DEBUG - Ver o que está chegando
        print(f"=== DEBUG CRIAÇÃO ATIVIDADE ===")
        print(f"Título: {titulo}")
        print(f"Descrição: {descricao}")
        print(f"Tipo: {tipo}")
        print(f"Ano 1: {ano_1}")
        print(f"Ano 2: {ano_2}")
        print(f"Ano 3: {ano_3}")
        print(f"Todos: {todos}")
        print(f"Prazo: {prazo_entrega}")
        print(f"Anexo: {anexo}")
        print(f"POST completo: {request.POST}")
        print(f"===========================")
        
        # ========================================
        # VALIDAÇÕES 
        # ========================================
        
        # 1. VALIDAR TÍTULO (50 CARACTERES, APENAS LETRAS E ESPAÇOS)
        if not titulo:
            messages.error(request, '❌ O título é obrigatório.')
            return redirect('atividades:lista')
            
        if len(titulo) > 50:
            messages.error(request, '❌ Título muito longo (máx 50 caracteres).')
            return redirect('atividades:lista')
        
        titulo_regex = r'^[A-Za-zÀ-ÿÇç\s]+$'
        if not re.match(titulo_regex, titulo):
            messages.error(request, '❌ Título contém caracteres não permitidos. Use apenas letras e espaços.')
            return redirect('atividades:lista')
        
        # 2. VALIDAR DESCRIÇÃO
        if not descricao:
            messages.error(request, '❌ A descrição é obrigatória.')
            return redirect('atividades:lista')
        
        # 3. VALIDAR PÚBLICO-ALVO
        if not any([ano_1, ano_2, ano_3, todos]):
            messages.error(request, '❌ Selecione pelo menos um ano ou "Todos".')
            return redirect('atividades:lista')
        
        # 4. VALIDAR TIPO
        if tipo not in ['ATIVIDADE', 'AVISO_PROVA', 'AVISO_SIMPLES']:
            messages.error(request, '❌ Selecione o tipo de atividade.')
            return redirect('atividades:lista')
        
        # 5. CRIAR ATIVIDADE
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
        
        # 6. VALIDAR E DEFINIR PRAZO (MÍNIMO 30 MINUTOS)
        if prazo_entrega:
            from django.utils.dateparse import parse_datetime
            prazo_dt = parse_datetime(prazo_entrega)
            
            if prazo_dt:
                # Tornar timezone-aware
                if timezone.is_naive(prazo_dt):
                    prazo_dt = timezone.make_aware(prazo_dt)
                
                limite_minimo = timezone.now() + timedelta(minutes=30)
                
                if prazo_dt < limite_minimo:
                    messages.error(request, '❌ O prazo deve ser no mínimo 30 minutos após agora.')
                    return redirect('atividades:lista')
                
                atividade.prazo_entrega = prazo_dt
        
        # 7. ANEXO
        if anexo:
            atividade.anexo = anexo
        
        # 8. DESABILITAR ENVIO PARA AVISOS
        if tipo in ['AVISO_PROVA', 'AVISO_SIMPLES']:
            atividade.permite_envio = False
        
        # 9. SALVAR NO BANCO DE DADOS
        atividade.save()
        
        print(f"✅ Atividade salva com ID: {atividade.id}")
        
        # 10. MENSAGEM DE SUCESSO
        anos_destino = atividade.get_anos_destino_display()
        messages.success(request, f'✅ Atividade "{titulo}" criada com sucesso para: {anos_destino}.')
        
        return redirect('atividades:lista')
        
    except Exception as e:
        print(f"❌ ERRO AO CRIAR ATIVIDADE: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'❌ Erro ao criar atividade: {str(e)}')
        return redirect('atividades:lista')


@login_required
def detalhe_atividade(request, pk):
    """
    Detalhe de atividade para aluno - CORRIGIDO: SEM BLOQUEIO DE ACESSO
    """
    atividade = get_object_or_404(Atividade, pk=pk)
    
    # Verificar se tem acesso
    tem_acesso = False
    
    # Se for professor criador
    if atividade.professor == request.user:
        tem_acesso = True
    
    # Se for aluno e a atividade é destinada para ele
    if request.user.user_type == 'aluno':
        tem_acesso = True
    
    if not tem_acesso:
        messages.error(request, 'Você não tem acesso a esta atividade.')
        return redirect('atividades:lista')
    
    # Registrar visualização (única) - APENAS PARA ALUNOS
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
    Gerar arquivo .ics para agendamento (CORRIGIDO CONFORME RELATÓRIO)
    """
    atividade = get_object_or_404(Atividade, pk=pk)
    
    if not atividade.prazo_entrega:
        messages.error(request, 'Esta atividade não possui prazo.')
        return redirect('atividades:detalhe', pk=pk)
    
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
    Criação de atividade por professor (PÁGINA SEPARADA - MANTIDA PARA COMPATIBILIDADE)
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