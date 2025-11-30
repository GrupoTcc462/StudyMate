from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_POST
from .models import Horario
from .forms import HorarioImportForm
import os


@login_required
def horarios_view(request):
    """
    View principal da aba Horários.
    Professores/admins veem botão de importar.
    Alunos veem apenas visualização/download.
    """
    user = request.user
    
    # Verificar se é professor ou admin
    is_professor_or_admin = user.user_type in ['professor', 'admin'] or user.is_staff or user.is_superuser
    
    # Buscar horário ativo
    horario_ativo = Horario.objects.filter(ativo=True).first()
    
    # Buscar histórico (apenas para professores/admins)
    historico = None
    if is_professor_or_admin:
        historico = Horario.objects.all()[:10]  # Últimas 10 versões
    
    # Processar importação (apenas para professores/admins)
    if request.method == 'POST' and is_professor_or_admin:
        form = HorarioImportForm(request.POST, request.FILES)
        
        if form.is_valid():
            horario = form.save(commit=False)
            horario.importado_por = user
            horario.save()
            
            messages.success(request, '✅ Horário inserido com sucesso!')
            return redirect('horarios:home')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = HorarioImportForm()
    
    context = {
        'is_professor_or_admin': is_professor_or_admin,
        'horario_ativo': horario_ativo,
        'historico': historico,
        'form': form,
    }
    
    return render(request, 'horarios/horarios.html', context)


@login_required
def baixar_horario(request, horario_id):
    """
    Download do arquivo de horário
    """
    horario = get_object_or_404(Horario, id=horario_id)
    
    file_path = horario.arquivo.path
    
    if not os.path.exists(file_path):
        raise Http404('Arquivo não encontrado no servidor')
    
    filename = os.path.basename(file_path)
    
    response = FileResponse(open(file_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
@require_POST
def confirmar_substituicao(request):
    """
    Confirmação antes de substituir horário
    (usado via AJAX se necessário)
    """
    user = request.user
    
    if not (user.user_type in ['professor', 'admin'] or user.is_staff or user.is_superuser):
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    return JsonResponse({'success': True})


@login_required
def visualizar_versao(request, horario_id):
    """
    Visualiza uma versão antiga do horário (modal ou página separada)
    """
    user = request.user
    
    # Verificar permissão
    if not (user.user_type in ['professor', 'admin'] or user.is_staff or user.is_superuser):
        messages.error(request, 'Você não tem permissão para acessar o histórico.')
        return redirect('horarios:home')
    
    horario = get_object_or_404(Horario, id=horario_id)
    
    context = {
        'horario': horario,
    }
    
    return render(request, 'horarios/visualizar_versao.html', context)