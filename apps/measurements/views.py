import io
import logging
import os
import re
import zipfile
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
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
PHOTOS_ZIP_MAX = 1000  # tope defensivo para no agotar memoria al exportar
PHOTOS_ZIP_DEFAULT_SUBDIR = 'fotos_mediciones'

SPANISH_MONTHS = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]


def _zip_safe_part(value, maxlen=80):
    """Sanitiza un fragmento para usarlo como nombre de carpeta/archivo en el ZIP."""
    s = (value or '').strip()
    s = re.sub(r'[^\w\s.-]', '', s, flags=re.UNICODE)
    s = re.sub(r'\s+', ' ', s).strip(' ._')
    return (s[:maxlen] or 'sin_dato')


def _tower_letter(name):
    """'Torre A' → 'A'; 'Torre 2' → '2'; 'Norte' → 'Norte'."""
    s = (name or '').strip()
    s = re.sub(r'^torre\s+', '', s, flags=re.IGNORECASE).strip()
    return s or (name or '').strip() or '?'


def _infer_period_label(measurements):
    """Si todas las mediciones caen en el mismo mes calendario, devuelve 'YYYY Mes' en español."""
    months = set()
    for m in measurements:
        if m.captured_at:
            months.add((m.captured_at.year, m.captured_at.month))
        if len(months) > 1:
            return ''
    if len(months) != 1:
        return ''
    y, mo = next(iter(months))
    return f'{y} {SPANISH_MONTHS[mo - 1]}'


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
    # Forma de diccionario para habilitar lookups por fecha además de los exactos.
    # `captured_at__year` y `captured_at__month` permiten que el panel pida solo el
    # mes en curso (mucho más rápido que descargar todo el histórico).
    filterset_fields = {
        'status': ['exact'],
        'meter_type': ['exact'],
        'apartment': ['exact'],
        'apartment__tower': ['exact'],
        'operator': ['exact'],
        'cycle': ['exact'],
        'captured_at': ['year', 'month', 'gte', 'lte'],
    }
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
        detail=False,
        methods=['get'],
        url_path='summary',
        permission_classes=[IsAdminUser],
    )
    def summary(self, request):
        """
        Agregados para el Dashboard sin descargar todas las filas.

        El panel ahora carga solo el mes en curso en la tabla de mediciones; este
        endpoint provee los totales/tendencias que el Dashboard necesita ver de
        todo el histórico (conteos por estado, últimos 6 meses, etc.).
        """
        base = _measurement_base_queryset(request.user).filter(deleted_at__isnull=True)

        # Conteos por estado (toda la organización, no solo el mes visible).
        status_counts = {row['status']: row['n'] for row in base.values('status').annotate(n=Count('id'))}

        # Validadas en los últimos 30 días (usa validated_at; si falta, captured_at).
        cutoff = timezone.now() - timedelta(days=30)
        verified_last_30 = (
            base.filter(status=Measurement.Status.VERIFIED)
            .filter(Q(validated_at__gte=cutoff) | Q(validated_at__isnull=True, captured_at__gte=cutoff))
            .count()
        )

        # Mediciones por mes, últimos 6 meses (incluye meses sin datos como 0).
        months = 6
        now = timezone.localtime()
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        anchor = first_of_month.year * 12 + (first_of_month.month - 1)
        start_anchor = anchor - (months - 1)
        start_year, start_month0 = divmod(start_anchor, 12)
        period_start = first_of_month.replace(year=start_year, month=start_month0 + 1)

        rows = (
            base.filter(captured_at__gte=period_start)
            .annotate(m=TruncMonth('captured_at'))
            .values('m')
            .annotate(n=Count('id'))
        )
        counts_by_ym = {}
        for row in rows:
            m = row['m']
            if m is not None:
                counts_by_ym[(m.year, m.month)] = row['n']

        monthly_counts = []
        for i in range(months):
            a = start_anchor + i
            y, m0 = divmod(a, 12)
            monthly_counts.append({'year': y, 'month': m0 + 1, 'count': counts_by_ym.get((y, m0 + 1), 0)})

        # Últimas 5 mediciones (para la lista de actividad reciente).
        recent = base.order_by('-captured_at')[:5]
        recent_data = MeasurementSerializer(recent, many=True, context={'request': request}).data

        return Response({
            'status_counts': {
                'verified': status_counts.get('verified', 0),
                'pending_review': status_counts.get('pending_review', 0),
                'rejected': status_counts.get('rejected', 0),
            },
            'verified_last_30_days': verified_last_30,
            'monthly_counts': monthly_counts,
            'recent': recent_data,
        })

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

    @action(
        detail=True,
        methods=['post'],
        url_path='reassign',
        permission_classes=[IsAdminUser],
    )
    def reassign(self, request, pk=None):
        """
        Reasigna la medición a otro departamento (p. ej., el operador escaneó un QR
        equivocado y se descubrió viendo la foto). Crea entrada en el historial.

        Body: { apartment_id: int, note?: str }
        """
        from apps.buildings.models import Apartment

        measurement = self.get_object()
        target_id = request.data.get('apartment_id')
        if target_id in (None, '', 0):
            return Response(
                {'apartment_id': 'Requerido. Indica el id del depto destino.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            target_id = int(target_id)
        except (TypeError, ValueError):
            return Response(
                {'apartment_id': 'apartment_id debe ser un entero.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # El admin debe tener acceso al edificio destino (mismo conjunto de orgs gestionadas).
        target_qs = Apartment.objects.select_related('tower__building')
        org_ids = _managed_org_ids(request.user)
        if org_ids is not None:
            target_qs = target_qs.filter(tower__building__organization_id__in=org_ids)
        target = target_qs.filter(pk=target_id).first()
        if target is None:
            return Response(
                {'apartment_id': 'No existe el departamento destino o no tienes acceso a su edificio.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        old_apt = measurement.apartment
        if old_apt.id == target.id:
            return Response(
                {'apartment_id': 'La medición ya pertenece a ese departamento.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        note = (request.data.get('note') or '').strip()[:500]
        old_label = f'{old_apt.tower.building.name} · {old_apt.tower.name} · {old_apt.number}'
        new_label = f'{target.tower.building.name} · {target.tower.name} · {target.number}'

        measurement.apartment = target
        measurement.save(update_fields=['apartment'])

        MeasurementAuditLog.objects.create(
            measurement=measurement,
            edited_by=request.user,
            field_name='apartment',
            old_value=old_label,
            new_value=new_label,
            note=note or 'Reasignación desde panel.',
        )

        ser = MeasurementDetailSerializer(measurement, context={'request': request})
        return Response(ser.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['post'],
        url_path='photos-zip',
        permission_classes=[IsAdminUser],
    )
    def photos_zip(self, request):
        """
        Devuelve un ZIP con las fotos de las mediciones indicadas, organizado en
        carpetas Edificio/Torre/. Una sola petición — evita 540 fetches desde el
        navegador y problemas de CORS sobre /media/.

        Body: { measurement_ids: [int, ...] }
        """
        ids = request.data.get('measurement_ids')
        if not isinstance(ids, list) or not ids:
            return Response(
                {'error': 'measurement_ids: lista no vacía requerida.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Filtra IDs válidos y aplica el tope defensivo.
        clean_ids = []
        for x in ids[:PHOTOS_ZIP_MAX]:
            try:
                clean_ids.append(int(x))
            except (TypeError, ValueError):
                continue
        if not clean_ids:
            return Response({'error': 'No hay IDs válidos.'}, status=status.HTTP_400_BAD_REQUEST)

        qs = (
            _measurement_base_queryset(request.user)
            .filter(id__in=clean_ids, deleted_at__isnull=True)
            .select_related('apartment__tower__building')
            .order_by(
                'apartment__tower__building__name',
                'apartment__tower__name',
                'apartment__floor',
                'apartment__number',
                'captured_at',
            )
        )

        # Etiqueta de período: la manda el frontend según filtros activos
        # (ej. "2026 Abril" o nombre de ciclo). Si no, intentamos inferir.
        period_label = (request.data.get('period_label') or '').strip()
        if not period_label:
            period_label = _infer_period_label(qs)

        buf = io.BytesIO()
        included = 0
        skipped = 0
        used_names = set()

        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
            for m in qs:
                if not m.photo:
                    skipped += 1
                    continue
                try:
                    with m.photo.open('rb') as f:
                        data = f.read()
                except Exception as e:  # archivo perdido / IO error → omitir
                    logger.warning('photos_zip: skip measurement %s — %s', m.pk, e)
                    skipped += 1
                    continue

                # Nivel 1: "Edificio YYYY Mes" (o solo "Edificio" si no hay etiqueta).
                building_name = m.apartment.tower.building.name
                building_dir = _zip_safe_part(
                    f'{building_name} {period_label}'.strip()
                )
                # Nivel 2: nombre de torre tal cual (ej. "Torre A").
                tower_dir = _zip_safe_part(m.apartment.tower.name)
                # Nivel 3: "P NN L" — piso 0-padded a 2 + letra de torre.
                floor_n = m.apartment.floor or 0
                tletter = _zip_safe_part(_tower_letter(m.apartment.tower.name), maxlen=8)
                floor_dir = f'P {floor_n:02d} {tletter}'
                # Archivo: Depto-NNN__YYYY-MM-DD_HHMMSS.ext
                apt = _zip_safe_part(m.apartment.number)
                stamp = m.captured_at.strftime('%Y-%m-%d_%H%M%S') if m.captured_at else 'sin_fecha'
                ext = (os.path.splitext(m.photo.name)[1] or '.jpg').lower()
                base = f'{building_dir}/{tower_dir}/{floor_dir}/Depto-{apt}__{stamp}'
                full = f'{base}{ext}'
                n = 2
                while full in used_names:
                    full = f'{base}_{n}{ext}'
                    n += 1
                used_names.add(full)
                zf.writestr(full, data)
                included += 1

        if included == 0:
            return Response(
                {'error': 'No hay fotos descargables para los IDs indicados.', 'skipped': skipped},
                status=status.HTTP_400_BAD_REQUEST,
            )

        buf.seek(0)
        response = HttpResponse(buf.getvalue(), content_type='application/zip')
        fname = f'{PHOTOS_ZIP_DEFAULT_SUBDIR}_{timezone.now().strftime("%Y%m%d_%H%M")}.zip'
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        response['X-Photos-Included'] = str(included)
        response['X-Photos-Skipped'] = str(skipped)
        # Permite al frontend leer estos headers cuando el browser aplique CORS.
        response['Access-Control-Expose-Headers'] = (
            'Content-Disposition, X-Photos-Included, X-Photos-Skipped'
        )
        return response


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
