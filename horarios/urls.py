from django.urls import path
from . import views

app_name = 'horarios'

urlpatterns = [
    # Página principal
    path('', views.horarios_view, name='home'),
    
    # Download de horário
    path('baixar/<int:horario_id>/', views.baixar_horario, name='baixar'),
    
    # Visualizar versão antiga
    path('versao/<int:horario_id>/', views.visualizar_versao, name='visualizar_versao'),
    
    # Confirmação de substituição (AJAX)
    path('confirmar-substituicao/', views.confirmar_substituicao, name='confirmar_substituicao'),
]