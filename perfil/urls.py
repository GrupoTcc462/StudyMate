from django.urls import path
from . import views

app_name = 'perfil'

urlpatterns = [
    # Visualização do perfil
    path('', views.perfil_view, name='perfil'),
    
    # Edição do perfil
    path('editar/', views.editar_perfil, name='editar'),
    
    # Validações em tempo real
    path('check_password/', views.check_password, name='check_password'),
    path('check-username/', views.check_username, name='check_username'),
    path('check-email/', views.check_email, name='check_email'),
    
    # Dados dos popups em tempo real
    path('popup-data/<str:tipo>/', views.popup_data, name='popup_data'),
]