import logging
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from .models import Measurement
from .serializers import MeasurementSerializer, MeasurementCreateSerializer
from . import ocr_service
from apps.accounts.views import IsAdminUser, _managed_org_ids

logger = logging.getLogger(__name__)

RETENTION_DAYS = 30


def _measurement_base_queryset(user):
    qs = Measurement.all_objects.select_related(
        'apartment__tower__building', 'operator',
    )
    if user.role == 'operator':
        return qs.filter(operator=user)
    org_ids = _managed_org_ids(user)
    if org_ids is None:
        return qs
    return qs.filter(apartment__tower__building__organization_id__in=org_ids)


class MeasurementViewSet(viewsets.ModelViewSet):
    """
    Admins see measurements within their org(s).
    Operators see only their own measurements.

    DELETE es eliminación lógica (30 días en papelera). Ver acciones `trash` y `restore`.
    """
    filterset_fields = ['status', 'meter_type', 'apartment', 'apartment__tower', 'operator']
    search_fields = ['apartment__number', 'apartment__meter_id', 'apartment__qr_code']
    ordering_fields = ['captured_at', 'reading_value', 'created_at']

    def get_queryset(self):
        user = self.request.user
        base = _measurement_base_queryset(user)
        if self.action == 'restore':
            return base.filter(deleted_at__isnull=False)
        return base.filter(deleted_at__isnull=True)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at'])

    def get_serializer_class(self):
        if self.action in ('create',):
            return MeasurementCreateSerializer
        return MeasurementSerializer

    @action(
        detail=False,
        methods=['get'],
        url_path='trash',
        permission_classes=[IsAdminUser],
    )
    def trash(self, request):
        """Mediciones eliminadas lógicamente en los últimos 30 días (recuperables)."""
        cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
        qs = (
            _measurement_base_queryset(request.user)
            .filter(deleted_at__isnull=False, deleted_at__gte=cutoff)
            .order_by('-deleted_at')
        )
        page = self.paginate_queryset(qs)
        ser = MeasurementSerializer(page or qs, many=True, context={'request': request})
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    @action(
        detail=True,
        methods=['post'],
        url_path='restore',
        permission_classes=[IsAdminUser],
    )
    def restore(self, request, pk=None):
        """Restaura una medición desde la papelera (si no expiró el plazo)."""
        cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
        qs = _measurement_base_queryset(request.user).filter(
            deleted_at__isnull=False,
            deleted_at__gte=cutoff,
        )
        measurement = get_object_or_404(qs, pk=pk)
        measurement.deleted_at = None
        measurement.save(update_fields=['deleted_at'])
        ser = MeasurementSerializer(measurement, context={'request': request})
        return Response(ser.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser])
def ocr_analyze(request):
    """
    Receive an image, save it to media, run Gemini OCR, return reading.

    POST /api/measurements/ocr/
    Body (multipart/form-data):
        - photo: image file (JPEG/PNG)
        - meter_reading_type: optional, "A" or "B" (default "A")
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
        meter_reading_type = request.POST.get('meter_reading_type')

        # Run OCR via Gemini
        ocr_value = ocr_service.recognize_from_bytes(
            image_bytes,
            meter_reading_type=meter_reading_type,
        )

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
