from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.views import IsAdminUser
from apps.measurements.models import Measurement
from .models import MeasurementCycle
from .serializers import (
    MeasurementCycleSerializer,
    MeasurementCycleCreateSerializer,
    CycleProgressApartmentSerializer,
)


class MeasurementCycleViewSet(viewsets.ModelViewSet):
    queryset = MeasurementCycle.objects.select_related('building').all()
    permission_classes = [IsAdminUser]
    filterset_fields = ['building', 'year', 'month', 'status']
    ordering_fields = ['year', 'month', 'scheduled_date', 'deadline']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return MeasurementCycleCreateSerializer
        return MeasurementCycleSerializer

    @action(detail=False, methods=['get'], url_path='current',
            permission_classes=[IsAdminUser])
    def current(self, request):
        """Return all in_progress cycles, or the most recent pending one per building."""
        active = MeasurementCycle.objects.filter(
            status__in=['pending', 'in_progress']
        ).select_related('building').order_by('-year', '-month')
        serializer = MeasurementCycleSerializer(active, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='progress',
            permission_classes=[IsAdminUser])
    def progress(self, request, pk=None):
        """Detailed apartment-level progress for a cycle."""
        cycle = self.get_object()
        apartments = cycle.get_target_apartments().select_related(
            'tower'
        ).order_by('tower__name', 'floor', 'number')

        measurements = {
            m.apartment_id: m
            for m in Measurement.objects.filter(
                apartment__in=apartments,
                captured_at__date__gte=cycle.scheduled_date,
                captured_at__date__lte=cycle.deadline,
            ).select_related('operator').order_by('apartment_id', '-captured_at')
        }

        rows = []
        for apt in apartments:
            m = measurements.get(apt.id)
            rows.append({
                'apartment_id': apt.id,
                'apartment_number': apt.number,
                'floor': apt.floor,
                'meter_id': apt.meter_id,
                'tower_name': apt.tower.name,
                'measured': m is not None,
                'measurement_id': m.id if m else None,
                'reading_value': m.reading_value if m else None,
                'captured_at': m.captured_at if m else None,
                'operator_name': (m.operator.get_full_name() or m.operator.username) if (m and m.operator) else None,
                'measurement_status': m.status if m else None,
            })

        serializer = CycleProgressApartmentSerializer(rows, many=True)
        return Response({
            'cycle': MeasurementCycleSerializer(cycle).data,
            'apartments': serializer.data,
        })
