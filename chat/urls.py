from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Lista de chats
    path('', views.lista_chats, name='lista'),
    
    # Conversa específica
    path('<int:chat_id>/', views.conversa, name='conversa'),
    
    # Nova conversa
    path('novo/', views.nova_conversa, name='novo'),
    
    # Apagar mensagens
    path('apagar/', views.apagar_mensagens, name='apagar'),
    
    # Baixar anexo
    path('anexo/<int:mensagem_id>/', views.baixar_anexo, name='anexo'),
    
    # Marcar como lida
    path('lida/<int:mensagem_id>/', views.marcar_como_lida, name='lida'),
]