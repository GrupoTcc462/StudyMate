from django.urls import path
from . import views

app_name = 'atividades'

urlpatterns = [
    # ALUNOS
    path('', views.lista_atividades, name='lista'),
    path('<int:pk>/', views.detalhe_atividade, name='detalhe'),
    path('<int:pk>/enviar/', views.enviar_atividade, name='enviar'),
    path('<int:pk>/salvar/', views.salvar_atividade, name='salvar'),
    path('<int:pk>/anexo/', views.baixar_anexo, name='baixar_anexo'),
    path('<int:pk>/agendar/', views.gerar_ics, name='gerar_ics'),
    
    # PROFESSORES
    path('professor/', views.painel_professor, name='painel_professor'),
    path('professor/criar/', views.criar_atividade, name='criar'),
    path('professor/<int:pk>/envios/', views.ver_envios, name='ver_envios'),
    path('professor/envio/<int:pk>/baixar/', views.baixar_envio, name='baixar_envio'),
    path('professor/<int:pk>/excluir/', views.excluir_atividade, name='excluir'),
]