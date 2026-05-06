"""Sirve MEDIA_ROOT con las mismas orígenes CORS que la API (fetch / ZIP desde el admin)."""
from django.conf import settings
from django.views.static import serve


def serve_media_with_cors(request, path):
    resp = serve(request, path, document_root=str(settings.MEDIA_ROOT))
    origin = request.headers.get('Origin')
    allowed = list(getattr(settings, 'CORS_ALLOWED_ORIGINS', []) or ())
    if origin and origin in allowed:
        resp['Access-Control-Allow-Origin'] = origin
        resp['Access-Control-Allow-Credentials'] = 'true'
    return resp
