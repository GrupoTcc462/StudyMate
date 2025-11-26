from django.urls import path
from . import views

app_name = 'materias'

urlpatterns = [
    path('', views.materias_home, name='home'),
    path('<slug:slug>/', views.subject_detail, name='detail'),
]