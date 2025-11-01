from django.urls import path
from . import views

app_name = 'notes'

urlpatterns = [
    path('', views.notes_list, name='list'),
    path('<int:pk>/', views.note_detail, name='detail'),
    path('create/', views.note_create, name='create'),
    path('<int:pk>/like/', views.like_note, name='like'),
    path('<int:pk>/download/', views.download_note, name='download'),
    path('<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('<int:pk>/recommend/', views.toggle_recommend, name='toggle_recommend'),
]