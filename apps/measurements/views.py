from rest_framework import viewsets, permissions
from .models import Measurement
from .serializers import MeasurementSerializer, MeasurementCreateSerializer


class MeasurementViewSet(viewsets.ModelViewSet):
    """
    Admins see all measurements.
    Operators see only their own.
    """
    filterset_fields = ['status', 'meter_type', 'apartment', 'apartment__tower', 'operator']
    search_fields = ['apartment__number', 'apartment__meter_id']
    ordering_fields = ['captured_at', 'reading_value', 'created_at']

    def get_queryset(self):
        qs = Measurement.objects.select_related(
            'apartment__tower__building', 'operator',
        ).all()
        if self.request.user.role == 'operator':
            qs = qs.filter(operator=self.request.user)
        return qs

    def get_serializer_class(self):
        if self.action in ('create',):
            return MeasurementCreateSerializer
        return MeasurementSerializer
