import logging
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from .models import Measurement, MeasurementAuditLog
from .serializers import (
    MeasurementSerializer,
    MeasurementCreateSerializer,
    MeasurementDetailSerializer,
    MeasurementAdminUpdateSerializer,
)
from . import ocr_service
from apps.accounts.views import IsAdminUser, _managed_org_ids
from apps.notifications.models import Notification

logger = logging.getLogger(__name__)

RETENTION_DAYS = 30


def _measurement_base_queryset(user):
    qs = Measurement.all_objects.select_related(
        'apartment__tower__building', 'operator', 'cycle', 'cycle__building',
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
        qs = base.filter(deleted_at__isnull=True)
        if self.action == 'retrieve':
            qs = qs.prefetch_related('audit_logs__edited_by')
        return qs

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at'])

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MeasurementDetailSerializer
        if self.action in ('update', 'partial_update'):
            return MeasurementAdminUpdateSerializer
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

    @action(
        detail=True,
        methods=['post'],
        url_path='validate',
        permission_classes=[IsAdminUser],
    )
    def validate_measurement(self, request, pk=None):
        """Valida (verifica) la medición y registra al admin que lo hizo."""
        measurement = self.get_object()
        old_status = measurement.status
        now = timezone.now()

        measurement.status = Measurement.Status.VERIFIED
        measurement.validated_by = request.user
        measurement.validated_at = now
        measurement.rejected_by = None
        measurement.rejected_at = None
        measurement.rejection_category = ''
        measurement.rejection_reason = ''
        measurement.save(update_fields=[
            'status', 'validated_by', 'validated_at',
            'rejected_by', 'rejected_at', 'rejection_category', 'rejection_reason',
        ])

        if old_status != measurement.status:
            MeasurementAuditLog.objects.create(
                measurement=measurement,
                edited_by=request.user,
                field_name='status',
                old_value=old_status,
                new_value=measurement.status,
                note='Validación desde el panel.',
            )

        if measurement.operator_id:
            Notification.objects.create(
                recipient=measurement.operator,
                type=Notification.Type.MEASUREMENT_VALIDATED,
                title='Medición validada',
                body=f'Tu medición del depto {measurement.apartment.number} fue validada.',
                measurement=measurement,
                payload={
                    'measurement_id': measurement.id,
                    'apartment_number': measurement.apartment.number,
                },
            )

        ser = MeasurementDetailSerializer(measurement, context={'request': request})
        return Response(ser.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['post'],
        url_path='reject',
        permission_classes=[IsAdminUser],
    )
    def reject_measurement(self, request, pk=None):
        """Rechaza la medición con motivo (categoría + nota) y notifica al operador."""
        measurement = self.get_object()
        category = (request.data.get('category') or '').strip()
        reason = (request.data.get('reason') or '').strip()[:1000]

        valid_categories = {c.value for c in Measurement.RejectionCategory}
        if category not in valid_categories:
            return Response(
                {'category': f'Categoría inválida. Opciones: {", ".join(sorted(valid_categories))}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = measurement.status
        now = timezone.now()
        measurement.status = Measurement.Status.REJECTED
        measurement.rejected_by = request.user
        measurement.rejected_at = now
        measurement.rejection_category = category
        measurement.rejection_reason = reason
        measurement.validated_by = None
        measurement.validated_at = None
        measurement.save(update_fields=[
            'status', 'rejected_by', 'rejected_at',
            'rejection_category', 'rejection_reason',
            'validated_by', 'validated_at',
        ])

        if old_status != measurement.status:
            MeasurementAuditLog.objects.create(
                measurement=measurement,
                edited_by=request.user,
                field_name='status',
                old_value=old_status,
                new_value=measurement.status,
                note=(f'Rechazo ({category}). {reason}')[:500],
            )

        if measurement.operator_id:
            category_label = dict(Measurement.RejectionCategory.choices).get(category, category)
            body = f'Tu medición del depto {measurement.apartment.number} fue rechazada por: {category_label}.'
            if reason:
                body += f' Detalle: {reason}'
            body += ' Debes volver a medir este departamento.'
            Notification.objects.create(
                recipient=measurement.operator,
                type=Notification.Type.MEASUREMENT_REJECTED,
                title='Medición rechazada',
                body=body,
                measurement=measurement,
                payload={
                    'measurement_id': measurement.id,
                    'apartment_id': measurement.apartment_id,
                    'apartment_number': measurement.apartment.number,
                    'category': category,
                    'reason': reason,
                },
            )

        ser = MeasurementDetailSerializer(measurement, context={'request': request})
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
