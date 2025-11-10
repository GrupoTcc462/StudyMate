from django.urls import path
from . import views

app_name = 'perfil'  # ← ESTA LINHA ESTAVA FALTANDO!

urlpatterns = [
    path('', views.perfil_view, name='perfil'),
    path('editar-nome/', views.editar_nome, name='editar_nome'),
]