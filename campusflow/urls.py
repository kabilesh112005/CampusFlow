from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # accounts app
    path('', include('accounts.urls')),

    # redirect root
    path('', lambda request: redirect('login'), name='home'),
]

# ✅ ADD MEDIA SUPPORT (correct way)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)