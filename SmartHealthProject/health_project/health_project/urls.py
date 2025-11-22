# health_project/urls.py

from django.contrib import admin
from django.urls import path, include  # <-- 1. Add 'include'
from django.conf import settings              # <-- 1. ADD THIS
from django.conf.urls.static import static  # <-- 2. ADD THIS

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),  # <-- 2. Add this line
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)