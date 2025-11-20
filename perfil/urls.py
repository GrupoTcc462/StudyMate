from django.urls import path
from . import views

app_name = 'perfil'

urlpatterns = [
    path('', views.perfil_view, name='perfil'),
    path('editar/', views.editar_perfil, name='editar'),  # Nova rota
    path('check_password/', views.check_password, name='check_password'),  # Nova rota
]