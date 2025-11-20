from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Autenticação
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Cadastro multietapas
    path('register/', views.register_view, name='register'),
    path('send-verification-code/', views.send_verification_code, name='send_verification_code'),
    path('verify-code/', views.verify_code, name='verify_code'),
    path('create-account/', views.create_account, name='create_account'),
    path('check-session/', views.check_session, name='check_session'),
]