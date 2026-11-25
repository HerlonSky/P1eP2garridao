from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # API REST (DRF) separada das páginas, sempre com o prefixo /api/.
    path('api/', include('financas.api_urls')),
    # Login/logout da Browsable API do DRF.
    path('api-auth/', include('rest_framework.urls')),
    path('', include('financas.urls')),
]
