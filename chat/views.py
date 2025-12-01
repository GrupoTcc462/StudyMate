from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q, Max, Count, F
from django.utils import timezone
from .models import Chat, Mensagem, MensagemApagada
from .forms import MensagemForm
from accounts.models import User
import os
import mimetypes


@login_required
def lista_chats(request):
    """
    Lista todos os chats do usuário com informações de última mensagem
    """
    user = request.user
    
    chats = Chat.objects.filter(
        Q(remetente=user) | Q(destinatario=user)
    ).annotate(
        ultima_mensagem_data=Max('mensagens__data_envio')
    ).order_by('-ultima_mensagem_data')
    
    filtro = request.GET.get('filtro', '')
    
    if filtro == 'nao_lidos':
        chats = [chat for chat in chats if chat.get_mensagens_nao_lidas(user) > 0]
    
    chats_data = []
    for chat in chats:
        outro_usuario = chat.get_outro_usuario(user)
        ultima_msg = chat.get_ultima_mensagem()
        nao_lidas = chat.get_mensagens_nao_lidas(user)
        
        chats_data.append({
            'chat': chat,
            'outro_usuario': outro_usuario,
            'ultima_mensagem': ultima_msg,
            'nao_lidas': nao_lidas,
        })
    
    context = {
        'chats_data': chats_data,
        'filtro_atual': filtro,
    }
    
    return render(request, 'chat/lista_chats.html', context)


@login_required
def conversa(request, chat_id):
    """
    Exibe a conversa de um chat específico - CORRIGIDO: RASCUNHOS
    """
    chat = get_object_or_404(Chat, id=chat_id)
    user = request.user
    
    if user not in [chat.remetente, chat.destinatario]:
        messages.error(request, 'Você não tem acesso a este chat.')
        return redirect('chat:lista')
    
    outro_usuario = chat.get_outro_usuario(user)
    
    mensagens_apagadas_ids = MensagemApagada.objects.filter(
        usuario=user
    ).values_list('mensagem_id', flat=True)
    
    mensagens = chat.mensagens.exclude(
        id__in=mensagens_apagadas_ids
    ).select_related('remetente').order_by('data_envio')
    
    mensagens.filter(
        remetente=outro_usuario,
        lida=False
    ).update(lida=True, data_leitura=timezone.now())
    
    # PROCESSAR ENVIO DE MENSAGEM
    if request.method == 'POST':
        form = MensagemForm(request.POST, request.FILES)
        if form.is_valid():
            mensagem = form.save(commit=False)
            mensagem.chat = chat
            mensagem.remetente = user
            mensagem.save()
            
            # LIMPAR RASCUNHO APÓS ENVIO
            draft_key = f'chat_draft_{chat.id}_{user.id}'
            if draft_key in request.session:
                del request.session[draft_key]
            
            messages.success(request, 'Mensagem enviada!')
            return redirect('chat:conversa', chat_id=chat.id)
    else:
        form = MensagemForm()
    
    # RECUPERAR RASCUNHO (se houver)
    draft_key = f'chat_draft_{chat.id}_{user.id}'
    draft_text = request.session.get(draft_key, '')
    
    context = {
        'chat': chat,
        'outro_usuario': outro_usuario,
        'mensagens': mensagens,
        'form': form,
        'draft_text': draft_text,
    }
    
    return render(request, 'chat/conversa.html', context)


@login_required
def nova_conversa(request):
    """
    CORRIGIDO - Busca sem limite mínimo de caracteres
    """
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        
        # BUSCA SEM LIMITE MÍNIMO
        if query:
            usuarios = User.objects.filter(
                Q(username__icontains=query) | Q(email__icontains=query)
            ).exclude(id=request.user.id)[:20]
        else:
            # SEM QUERY: LISTAR TODOS OS USUÁRIOS
            usuarios = User.objects.exclude(id=request.user.id)[:50]
        
        # Se for requisição AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            resultados = [{
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'user_type': u.get_user_type_display()
            } for u in usuarios]
            
            return JsonResponse({'resultados': resultados})
        
        # Renderizar página normal
        return render(request, 'chat/nova_conversa.html', {'usuarios': usuarios})
    
    # POST - Criar novo chat
    if request.method == 'POST':
        destinatario_id = request.POST.get('destinatario_id')
        
        if not destinatario_id:
            messages.error(request, 'Selecione um usuário.')
            return redirect('chat:novo')
        
        try:
            destinatario = User.objects.get(id=destinatario_id)
        except User.DoesNotExist:
            messages.error(request, 'Usuário não encontrado.')
            return redirect('chat:novo')
        
        chat = Chat.objects.filter(
            Q(remetente=request.user, destinatario=destinatario) |
            Q(remetente=destinatario, destinatario=request.user)
        ).first()
        
        if not chat:
            chat = Chat.objects.create(
                remetente=request.user,
                destinatario=destinatario
            )
            messages.success(request, f'Chat iniciado com {destinatario.username}!')
        else:
            messages.info(request, f'Você já tem uma conversa com {destinatario.username}.')
        
        return redirect('chat:conversa', chat_id=chat.id)
    
    return render(request, 'chat/nova_conversa.html')


@login_required
@require_POST
def save_draft(request):
    """
    NOVA VIEW - Salva rascunho de mensagem
    """
    import json
    
    try:
        data = json.loads(request.body)
        chat_id = data.get('chat_id')
        text = data.get('text', '')
        
        if not chat_id:
            return JsonResponse({'success': False, 'error': 'Chat ID não fornecido'}, status=400)
        
        # Verificar se chat existe e usuário tem acesso
        chat = Chat.objects.filter(
            Q(remetente=request.user) | Q(destinatario=request.user),
            id=chat_id
        ).first()
        
        if not chat:
            return JsonResponse({'success': False, 'error': 'Chat não encontrado'}, status=404)
        
        # Salvar rascunho na sessão
        draft_key = f'chat_draft_{chat_id}_{request.user.id}'
        
        if text.strip():
            request.session[draft_key] = text
            request.session['draft_timestamp'] = timezone.now().isoformat()
        else:
            # Remover rascunho se texto estiver vazio
            if draft_key in request.session:
                del request.session[draft_key]
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def clear_old_drafts(request):
    """
    NOVA VIEW - Limpa rascunhos com mais de 30 minutos
    """
    if 'draft_timestamp' in request.session:
        from datetime import datetime
        timestamp = datetime.fromisoformat(request.session['draft_timestamp'])
        
        if (timezone.now() - timestamp).total_seconds() > 1800:  # 30 minutos
            # Remover todos os rascunhos do usuário
            keys_to_delete = [k for k in request.session.keys() if k.startswith(f'chat_draft_')]
            for key in keys_to_delete:
                del request.session[key]
            
            if 'draft_timestamp' in request.session:
                del request.session['draft_timestamp']
    
    return JsonResponse({'success': True})


@login_required
@require_POST
def apagar_mensagens(request):
    """
    Apaga mensagens selecionadas (apenas para o usuário)
    """
    import json
    
    try:
        data = json.loads(request.body)
        mensagens_ids = data.get('mensagens_ids', [])
        
        if not mensagens_ids:
            return JsonResponse({
                'success': False,
                'error': 'Nenhuma mensagem selecionada.'
            }, status=400)
        
        mensagens = Mensagem.objects.filter(
            id__in=mensagens_ids,
            chat__in=Chat.objects.filter(
                Q(remetente=request.user) | Q(destinatario=request.user)
            )
        )
        
        for mensagem in mensagens:
            MensagemApagada.objects.get_or_create(
                mensagem=mensagem,
                usuario=request.user
            )
        
        return JsonResponse({
            'success': True,
            'message': f'{len(mensagens)} mensagem(ns) apagada(s).'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao apagar mensagens: {str(e)}'
        }, status=500)


@login_required
def baixar_anexo(request, mensagem_id):
    """
    Baixa anexo de uma mensagem
    """
    mensagem = get_object_or_404(Mensagem, id=mensagem_id)
    
    if request.user not in [mensagem.chat.remetente, mensagem.chat.destinatario]:
        raise Http404('Acesso negado')
    
    if not mensagem.anexo:
        raise Http404('Anexo não encontrado')
    
    file_path = mensagem.anexo.path
    
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
def marcar_como_lida(request, mensagem_id):
    """
    Marca mensagem como lida via AJAX
    """
    mensagem = get_object_or_404(Mensagem, id=mensagem_id)
    
    outro_usuario = mensagem.chat.get_outro_usuario(request.user)
    if mensagem.remetente == outro_usuario:
        mensagem.marcar_como_lida()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False}, status=403)