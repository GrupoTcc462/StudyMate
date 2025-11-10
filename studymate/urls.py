from django.contrib import admin
from django.urls import path, include
from django.conf import settings  
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    # Redirecionamento da raiz para /study/
    path('', lambda request: redirect('study/', permanent=False)),
    
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('study/', include('study.urls', namespace='study')),
    path('notes/', include('notes.urls', namespace='notes')),
    path('perfil/', include('perfil.urls', namespace='perfil')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)