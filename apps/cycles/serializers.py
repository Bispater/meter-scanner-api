from rest_framework import serializers
from .models import MeasurementCycle


class MeasurementCycleSerializer(serializers.ModelSerializer):
    building_name = serializers.CharField(source='building.name', read_only=True)
    month_name = serializers.CharField(read_only=True)
    total_apartments = serializers.SerializerMethodField()
    measured_count = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()
    progress_pct = serializers.SerializerMethodField()

    class Meta:
        model = MeasurementCycle
        fields = [
            'id', 'name', 'building', 'building_name',
            'year', 'month', 'month_name',
            'scheduled_date', 'deadline', 'status', 'notes',
            'created_at',
            'total_apartments', 'measured_count', 'pending_count', 'progress_pct',
        ]
        read_only_fields = ['id', 'created_at']

    def _get_measurements(self, obj):
        """All measurements whose captured_at falls inside the cycle window."""
        from apps.measurements.models import Measurement
        return Measurement.objects.filter(
            apartment__tower__building=obj.building,
            captured_at__date__gte=obj.scheduled_date,
            captured_at__date__lte=obj.deadline,
        )

    def get_total_apartments(self, obj):
        from apps.buildings.models import Apartment
        return Apartment.objects.filter(tower__building=obj.building).count()

    def get_measured_count(self, obj):
        return self._get_measurements(obj).values('apartment').distinct().count()

    def get_pending_count(self, obj):
        return self.get_total_apartments(obj) - self.get_measured_count(obj)

    def get_progress_pct(self, obj):
        total = self.get_total_apartments(obj)
        if total == 0:
            return 100
        return round(self.get_measured_count(obj) / total * 100)


class MeasurementCycleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeasurementCycle
        fields = [
            'id', 'name', 'building', 'year', 'month',
            'scheduled_date', 'deadline', 'status', 'notes',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        year = attrs.get('year')
        month = attrs.get('month')
        if month and not (1 <= month <= 12):
            raise serializers.ValidationError({'month': 'El mes debe estar entre 1 y 12.'})
        scheduled = attrs.get('scheduled_date')
        deadline = attrs.get('deadline')
        if scheduled and deadline and deadline < scheduled:
            raise serializers.ValidationError({
                'deadline': 'La fecha límite no puede ser anterior a la fecha programada.'
            })
        return attrs


class CycleProgressApartmentSerializer(serializers.Serializer):
    """One row in the cycle progress table."""
    apartment_id = serializers.IntegerField()
    apartment_number = serializers.CharField()
    floor = serializers.IntegerField()
    meter_id = serializers.CharField()
    tower_name = serializers.CharField()
    measured = serializers.BooleanField()
    measurement_id = serializers.IntegerField(allow_null=True)
    reading_value = serializers.DecimalField(max_digits=12, decimal_places=3, allow_null=True)
    captured_at = serializers.DateTimeField(allow_null=True)
    operator_name = serializers.CharField(allow_null=True)
    measurement_status = serializers.CharField(allow_null=True)
