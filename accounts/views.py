from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import User
from django.contrib.auth.forms import UserCreationForm

# 🔹 Registro de usuário
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        user_type = request.POST.get('user_type')

        if password1 != password2:
            messages.error(request, 'As senhas não coincidem.')
            return redirect('accounts:register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Esse nome de usuário já existe.')
            return redirect('accounts:register')

        user = User.objects.create_user(username=username, password=password1, user_type=user_type)
        messages.success(request, 'Cadastro realizado com sucesso!')
        return redirect('accounts:login')

    return render(request, 'accounts/register.html')

# 🔹 Login de usuário (ATUALIZADO)
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Bem-vindo(a) de volta ao StudyMate, {user.username}!')  # MENSAGEM ADICIONADA
            return redirect('study:home')
        else:
            messages.error(request, 'Usuário ou senha incorretos.')
            return redirect('accounts:login')

    return render(request, 'accounts/login.html')

# 🔹 Logout de usuário
def logout_view(request):
    logout(request)
    messages.info(request, 'Você saiu da sua conta.')
    return redirect('accounts:login')