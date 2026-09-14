from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/admin/', include('AdminApp.urls')),
    path('api/', include('userApp.urls')),
]
