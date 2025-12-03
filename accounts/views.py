from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import json
import random
import re
from .models import User


# ========================================
# LOGIN DE USUÁRIO (ATUALIZADO - ACEITA USERNAME OU EMAIL)
# ========================================
def login_view(request):
    if request.method == 'POST':
        credential = request.POST.get('credential', '').strip()
        password = request.POST.get('password')

        # Verificar se é um e-mail
        email_pattern = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
        institutional_pattern = re.compile(r'^[a-z0-9._%+-]+@etec\.sp\.gov\.br$', re.IGNORECASE)
        
        user = None
        
        if email_pattern.match(credential):
            # É um e-mail
            if not institutional_pattern.match(credential):
                messages.error(request, 'Use um e-mail institucional válido (@etec.sp.gov.br)')
                return redirect('accounts:login')
            
            # Buscar usuário pelo e-mail
            try:
                user_obj = User.objects.get(email__iexact=credential)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        else:
            # É um nome de usuário
            user = authenticate(request, username=credential, password=password)

        if user is not None:
            login(request, user)
            
            # Verificar se é primeiro login
            if not hasattr(user, 'perfil') or user.perfil.last_login_date is None:
                messages.success(
                    request, 
                    '🎉 Seja bem-vindo ao StudyMate! Suas informações pessoais podem ser '
                    'alteradas na aba Perfil → Editar perfil. '
                    '🔴 Alterações permitidas somente a cada 7 dias.'
                )
            else:
                messages.success(request, f'Bem-vindo(a) de volta ao StudyMate, {user.username}!')
            
            return redirect('study:home')
        else:
            messages.error(request, 'Usuário/E-mail ou senha incorretos.')
            return redirect('accounts:login')

    return render(request, 'accounts/login.html')


# ========================================
# LOGOUT DE USUÁRIO
# ========================================
def logout_view(request):
    logout(request)
    return redirect('accounts:login')


# ========================================
# CADASTRO - PÁGINA INICIAL
# ========================================
def register_view(request):
    """
    Renderiza a página de cadastro multietapas
    """
    return render(request, 'accounts/cadastro.html')


# ========================================
# ETAPA 1: ENVIAR CÓDIGO DE VERIFICAÇÃO
# ========================================
@require_http_methods(["POST"])
def send_verification_code(request):
    """
    Valida e-mail institucional, detecta tipo de usuário e envia código
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        user_type = data.get('user_type', '')

        # Validar formato de e-mail institucional
        email_regex = r'^[a-z0-9._%+-]+@etec\.sp\.gov\.br$'
        if not re.match(email_regex, email):
            return JsonResponse({
                'success': False,
                'error': 'Use um e-mail institucional válido (@etec.sp.gov.br).'
            }, status=400)

        # Verificar se e-mail já está cadastrado
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'error': 'Este e-mail já está registrado.'
            }, status=400)

        # Gerar código de 6 dígitos
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Definir expiração (30 minutos)
        expires_at = timezone.now() + timedelta(minutes=30)

        # Salvar na sessão
        request.session['cadastro_email'] = email
        request.session['cadastro_codigo'] = code
        request.session['cadastro_expira_em'] = expires_at.isoformat()
        request.session['cadastro_user_type'] = user_type
        request.session['cadastro_etapa'] = 2
        request.session['tentativas_codigo'] = 0

        # Enviar e-mail (IMPORTANTE: Configure SMTP no settings.py)
        try:
            send_mail(
                subject='Código de Verificação - StudyMate',
                message=f'Seu código de verificação é: {code}\n\nEste código expira em 30 minutos.',
                from_email='noreply@studymate.com',
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            # Se falhar, ainda permite prosseguir (desenvolvimento)
            print(f"Erro ao enviar e-mail: {e}")
            print(f"CÓDIGO DE VERIFICAÇÃO (DEV): {code}")

        return JsonResponse({
            'success': True,
            'expires_at': expires_at.isoformat()
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao processar requisição: {str(e)}'
        }, status=500)


# ========================================
# ETAPA 2: VERIFICAR CÓDIGO
# ========================================
@require_http_methods(["POST"])
def verify_code(request):
    """
    Valida código de verificação e controla expiração
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        code = data.get('code', '').strip()

        # Validar sessão
        saved_email = request.session.get('cadastro_email')
        saved_code = request.session.get('cadastro_codigo')
        expires_at_str = request.session.get('cadastro_expira_em')

        if not all([saved_email, saved_code, expires_at_str]):
            return JsonResponse({
                'success': False,
                'error': 'Sessão expirada. Reinicie o cadastro.'
            }, status=400)

        # Verificar e-mail
        if email != saved_email:
            return JsonResponse({
                'success': False,
                'error': 'E-mail inválido.'
            }, status=400)

        # Verificar expiração
        expires_at = timezone.datetime.fromisoformat(expires_at_str)
        if timezone.now() > expires_at:
            return JsonResponse({
                'success': False,
                'error': '🔴 Código expirado. Gere um novo código.'
            }, status=400)

        # Verificar código
        tentativas = request.session.get('tentativas_codigo', 0)
        
        if code != saved_code:
            tentativas += 1
            request.session['tentativas_codigo'] = tentativas
            
            if tentativas >= 5:
                # Invalidar código após 5 tentativas
                request.session['cadastro_codigo'] = None
                return JsonResponse({
                    'success': False,
                    'error': 'Muitas tentativas incorretas. Gere um novo código.'
                }, status=400)
            
            return JsonResponse({
                'success': False,
                'error': f'Código incorreto. Tentativa {tentativas}/5.'
            }, status=400)

        # Código correto - avançar para etapa 3
        request.session['cadastro_etapa'] = 3
        request.session['cadastro_codigo_verificado'] = True

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao verificar código: {str(e)}'
        }, status=500)


# ========================================
# ETAPA 3: CRIAR CONTA
# ========================================
@require_http_methods(["POST"])
def create_account(request):
    """
    Cria usuário após validação completa
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        password_confirm = data.get('password_confirm', '')
        user_type = data.get('user_type', '')

        # Validar sessão
        saved_email = request.session.get('cadastro_email')
        codigo_verificado = request.session.get('cadastro_codigo_verificado')
        etapa = request.session.get('cadastro_etapa')

        if not all([saved_email, codigo_verificado, etapa == 3]):
            return JsonResponse({
                'success': False,
                'error': 'Sessão inválida. Reinicie o cadastro.'
            }, status=400)

        if email != saved_email:
            return JsonResponse({
                'success': False,
                'error': 'E-mail inválido.'
            }, status=400)

        # Validar senhas
        if password != password_confirm:
            return JsonResponse({
                'success': False,
                'error': 'As senhas não coincidem.'
            }, status=400)

        # Validar força da senha
        password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&]).{8,}$'
        if not re.match(password_regex, password):
            return JsonResponse({
                'success': False,
                'error': 'A senha não atende aos requisitos mínimos de segurança.'
            }, status=400)

        # Verificar duplicidade (novamente)
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'error': 'Este e-mail já está registrado.'
            }, status=400)

        # Criar username a partir do e-mail
        username = email.split('@')[0]
        
        # Garantir unicidade do username
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Criar usuário
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_type=user_type
        )

        # Fazer login automático
        login(request, user)

        # Limpar sessão de cadastro
        keys_to_delete = [
            'cadastro_email', 'cadastro_codigo', 'cadastro_expira_em',
            'cadastro_user_type', 'cadastro_etapa', 'tentativas_codigo',
            'cadastro_codigo_verificado'
        ]
        for key in keys_to_delete:
            if key in request.session:
                del request.session[key]

        return JsonResponse({
            'success': True,
            'redirect_url': '/study/'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao criar conta: {str(e)}'
        }, status=500)


# ========================================
# VERIFICAR SESSÃO (PARA RESTAURAÇÃO)
# ========================================
@require_http_methods(["GET"])
def check_session(request):
    """
    Verifica se há sessão de cadastro ativa
    """
    etapa = request.session.get('cadastro_etapa')
    email = request.session.get('cadastro_email')
    user_type = request.session.get('cadastro_user_type')
    expires_at_str = request.session.get('cadastro_expira_em')

    if not etapa:
        return JsonResponse({'valid': False})

    # Verificar expiração (se estiver na etapa 2)
    if etapa == 2 and expires_at_str:
        expires_at = timezone.datetime.fromisoformat(expires_at_str)
        if timezone.now() > expires_at:
            return JsonResponse({'valid': False})

    return JsonResponse({
        'valid': True,
        'step': etapa,
        'email': email,
        'user_type': user_type,
        'expires_at': expires_at_str
    })