import logging

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from .models import Measurement
from .serializers import MeasurementSerializer, MeasurementCreateSerializer
from . import ocr_service
from apps.accounts.views import _managed_org_ids

logger = logging.getLogger(__name__)


class MeasurementViewSet(viewsets.ModelViewSet):
    """
    Admins see measurements within their org(s).
    Operators see only their own measurements.
    """
    filterset_fields = ['status', 'meter_type', 'apartment', 'apartment__tower', 'operator']
    search_fields = ['apartment__number', 'apartment__meter_id', 'apartment__qr_code']
    ordering_fields = ['captured_at', 'reading_value', 'created_at']

    def get_queryset(self):
        user = self.request.user
        qs = Measurement.objects.select_related(
            'apartment__tower__building', 'operator',
        )
        if user.role == 'operator':
            return qs.filter(operator=user)
        org_ids = _managed_org_ids(user)
        if org_ids is None:
            return qs.all()
        return qs.filter(apartment__tower__building__organization_id__in=org_ids)

    def get_serializer_class(self):
        if self.action in ('create',):
            return MeasurementCreateSerializer
        return MeasurementSerializer


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser])
def ocr_analyze(request):
    """
    Receive an image, save it to media, run Gemini OCR, return reading.

    POST /api/measurements/ocr/
    Body (multipart/form-data):
        - photo: image file (JPEG/PNG)
    Response:
        { "ocr_value": "12345", "photo_url": "/media/measurements/2025/04/file.jpg" }
    """
    photo = request.FILES.get('photo')
    if not photo:
        return Response(
            {'error': 'Se requiere una imagen en el campo "photo".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        image_bytes = photo.read()

        # Run OCR via Gemini
        ocr_value = ocr_service.recognize_from_bytes(image_bytes)

        return Response({
            'ocr_value': ocr_value,
        }, status=status.HTTP_200_OK)

    except ValueError as e:
        logger.warning('OCR ValueError: %s', e)
        return Response({'error': str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except Exception as e:
        logger.exception('OCR unexpected error')
        return Response(
            {'error': f'Error procesando imagen: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
