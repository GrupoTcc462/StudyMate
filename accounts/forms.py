from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class UserRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'user_type', 'matricula', 'telefone', 'password1', 'password2']
        labels = {
            'username': 'Nome de Usuário',
            'email': 'E-mail',
            'user_type': 'Tipo de Usuário',
            'matricula': 'Matrícula',
            'telefone': 'Telefone',
            'password1': 'Senha',
            'password2': 'Confirmar Senha',
        }
        