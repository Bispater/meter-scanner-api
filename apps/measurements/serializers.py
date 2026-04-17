from rest_framework import serializers
from .models import Measurement


def _apartment_queryset():
    from apps.buildings.models import Apartment
    return Apartment.objects.all()


class _ApartmentPKField(serializers.PrimaryKeyRelatedField):
    """Custom field with lazy queryset and user-friendly error when apartment no longer exists."""

    def get_queryset(self):
        return _apartment_queryset()

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data)
        except serializers.ValidationError:
            raise serializers.ValidationError(
                'El departamento escaneado ya no existe en el sistema. '
                'Es posible que la torre o el departamento hayan sido eliminados. '
                'Contacte al administrador.'
            )


class MeasurementSerializer(serializers.ModelSerializer):
    tower_name = serializers.CharField(source='apartment.tower.name', read_only=True)
    building_name = serializers.CharField(source='apartment.tower.building.name', read_only=True)
    apartment_number = serializers.CharField(source='apartment.number', read_only=True)
    meter_id = serializers.CharField(source='apartment.meter_id', read_only=True)
    operator_name = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    retention_days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Measurement
        fields = [
            'id', 'apartment', 'operator', 'reading_value', 'ocr_value',
            'modified_by_user', 'unit',
            'photo', 'photo_url', 'status', 'meter_type',
            'latitude', 'longitude',
            'captured_at', 'created_at', 'deleted_at',
            # Read-only enriched fields
            'tower_name', 'building_name', 'apartment_number', 'meter_id',
            'operator_name', 'retention_days_remaining',
        ]
        read_only_fields = ['id', 'created_at', 'deleted_at']

    def get_retention_days_remaining(self, obj):
        if not obj.deleted_at:
            return None
        from django.utils import timezone
        from datetime import timedelta
        purge_at = obj.deleted_at + timedelta(days=30)
        delta = purge_at - timezone.now()
        return max(0, delta.days)

    def get_operator_name(self, obj):
        if obj.operator:
            return obj.operator.get_full_name() or obj.operator.username
        return None

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None


class MeasurementCreateSerializer(serializers.ModelSerializer):
    apartment = _ApartmentPKField()

    class Meta:
        model = Measurement
        fields = [
            'id', 'apartment', 'reading_value', 'ocr_value',
            'modified_by_user', 'unit',
            'photo', 'status', 'meter_type',
            'latitude', 'longitude', 'captured_at',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        apartment = attrs.get('apartment')
        request = self.context.get('request')

        if apartment and request and request.user.is_authenticated:
            user = request.user
            if user.role != 'admin':
                if not user.assigned_apartments.filter(pk=apartment.pk).exists():
                    raise serializers.ValidationError({
                        'apartment': (
                            'El departamento escaneado no está asignado a su usuario '
                            'o ha sido eliminado. Contacte al administrador.'
                        )
                    })

        if apartment:
            cycle = self._find_active_cycle(apartment)
            if cycle:
                attrs['_matched_cycle'] = cycle
            else:
                enforcing = self._any_enforcing_cycle(apartment)
                if enforcing:
                    raise serializers.ValidationError({
                        'apartment': (
                            f'El departamento {apartment.number} pertenece al ciclo '
                            f'"{enforcing.name}" que no está activo (estado: {enforcing.get_status_display()}). '
                            f'Solo se permiten mediciones mientras el ciclo esté "En Curso".'
                        )
                    })

        return attrs

    def _find_active_cycle(self, apartment):
        """Find an in_progress cycle that includes this apartment."""
        from apps.cycles.models import MeasurementCycle
        from django.utils import timezone
        today = timezone.now().date()

        cycles = MeasurementCycle.objects.filter(
            building=apartment.tower.building,
            status='in_progress',
            scheduled_date__lte=today,
            deadline__gte=today,
        ).prefetch_related('apartments')

        for cycle in cycles:
            if not cycle.apartments.exists():
                return cycle
            if cycle.apartments.filter(pk=apartment.pk).exists():
                return cycle
        return None

    def _any_enforcing_cycle(self, apartment):
        """Check if any enforcing cycle claims this apartment but is not in_progress."""
        from apps.cycles.models import MeasurementCycle
        cycles = MeasurementCycle.objects.filter(
            building=apartment.tower.building,
            enforce=True,
            status__in=['pending', 'completed', 'closed'],
        ).prefetch_related('apartments')

        for cycle in cycles:
            if not cycle.apartments.exists():
                return cycle
            if cycle.apartments.filter(pk=apartment.pk).exists():
                return cycle
        return None

    def create(self, validated_data):
        matched_cycle = validated_data.pop('_matched_cycle', None)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['operator'] = request.user
        if matched_cycle:
            validated_data['cycle'] = matched_cycle
        measurement = super().create(validated_data)
        if matched_cycle:
            self._check_cycle_completion(matched_cycle)
        return measurement

    @staticmethod
    def _check_cycle_completion(cycle):
        """Auto-set cycle to 'completed' when all target apartments have been measured."""
        target_apts = cycle.get_target_apartments()
        total = target_apts.count()
        if total == 0:
            return
        measured = (
            Measurement.objects
            .filter(
                apartment__in=target_apts,
                captured_at__date__gte=cycle.scheduled_date,
                captured_at__date__lte=cycle.deadline,
            )
            .values('apartment')
            .distinct()
            .count()
        )
        if measured >= total and cycle.status == 'in_progress':
            cycle.status = 'completed'
            cycle.save(update_fields=['status'])
