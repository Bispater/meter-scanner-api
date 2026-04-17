from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

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
    path('api/', include('apps.cycles.urls')),

    # OpenAPI / Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Serve media files (in production, consider using nginx instead)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
