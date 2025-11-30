from django.urls import path
from . import views

app_name = 'materias'

urlpatterns = [
    path('', views.materias_home, name='home'),
    path('api/<slug:slug>/links/', views.get_links_materia, name='get_links'),
]