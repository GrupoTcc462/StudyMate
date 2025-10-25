from django.contrib import admin
from django.urls import path, include
from django.conf import settings  
from django.conf.urls.static import static
from django.shortcuts import redirect


def root_redirect(request):
    """Redireciona a raiz do site para /study"""
    return redirect('study:home')


urlpatterns = [
    path('', root_redirect, name='root'),  
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('study/', include('study.urls', namespace='study')),
    path('notes/', include('notes.urls', namespace='notes')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)