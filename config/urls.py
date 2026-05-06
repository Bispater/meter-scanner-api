from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.media_views import serve_media_with_cors

urlpatterns = [
    path('api/health/', lambda _: JsonResponse({'status': 'ok'})),
    path('admin/', admin.site.urls),

    # JWT Auth
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # App APIs
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/buildings/', include('apps.buildings.urls')),
    path('api/measurements/', include('apps.measurements.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/', include('apps.cycles.urls')),

    # OpenAPI / Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # /media/: siempre pasan por Django (incluye DEBUG=False) para poder aplicar CORS.
    # Nginx frente al contenedor debe reenviar /media/* al upstream, no servir archivo estático solo.
    re_path(r'^media/(?P<path>.+)$', serve_media_with_cors, name='media_serve'),
]
