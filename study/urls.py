from django.urls import path
from . import views

app_name = 'study'

urlpatterns = [
    path('', views.home, name='home'),
    
    # API endpoints para atualização em tempo real
    path('api/stats/', views.stats_api, name='stats_api'),
    path('api/materias_count/', views.materias_count_api, name='materias_count'),
    path('api/notes_count/', views.notes_count_api, name='notes_count'),
    path('api/online_students/', views.online_students_api, name='online_students'),
]