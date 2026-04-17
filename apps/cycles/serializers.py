from rest_framework import serializers
from .models import MeasurementCycle


class MeasurementCycleSerializer(serializers.ModelSerializer):
    """Read serializer — includes computed progress fields."""
    building_name = serializers.CharField(source='building.name', read_only=True)
    month_name = serializers.CharField(read_only=True)
    total_apartments = serializers.SerializerMethodField()
    measured_count = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()
    progress_pct = serializers.SerializerMethodField()
    apartment_ids = serializers.SerializerMethodField()

    class Meta:
        model = MeasurementCycle
        fields = [
            'id', 'name', 'building', 'building_name',
            'year', 'month', 'month_name',
            'scheduled_date', 'deadline', 'status', 'enforce',
            'notes', 'created_at',
            'apartment_ids',
            'total_apartments', 'measured_count', 'pending_count', 'progress_pct',
        ]
        read_only_fields = ['id', 'created_at']

    def _target_apartments(self, obj):
        return obj.get_target_apartments()

    def _get_measurements(self, obj):
        from apps.measurements.models import Measurement
        target_ids = self._target_apartments(obj).values_list('id', flat=True)
        return Measurement.objects.filter(
            apartment_id__in=target_ids,
            captured_at__date__gte=obj.scheduled_date,
            captured_at__date__lte=obj.deadline,
        )

    def get_total_apartments(self, obj):
        return self._target_apartments(obj).count()

    def get_measured_count(self, obj):
        return self._get_measurements(obj).values('apartment').distinct().count()

    def get_pending_count(self, obj):
        return self.get_total_apartments(obj) - self.get_measured_count(obj)

    def get_progress_pct(self, obj):
        total = self.get_total_apartments(obj)
        if total == 0:
            return 100
        return round(self.get_measured_count(obj) / total * 100)

    def get_apartment_ids(self, obj):
        """Return explicitly assigned apartment IDs (empty list = all from building)."""
        return list(obj.apartments.values_list('id', flat=True))


class MeasurementCycleCreateSerializer(serializers.ModelSerializer):
    apartment_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
        write_only=True,
    )

    class Meta:
        model = MeasurementCycle
        fields = [
            'id', 'name', 'building', 'year', 'month',
            'scheduled_date', 'deadline', 'status', 'enforce',
            'notes', 'apartment_ids',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
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

    def create(self, validated_data):
        apt_ids = validated_data.pop('apartment_ids', [])
        cycle = super().create(validated_data)
        if apt_ids:
            from apps.buildings.models import Apartment
            apts = Apartment.objects.filter(
                id__in=apt_ids,
                tower__building=cycle.building,
            )
            cycle.apartments.set(apts)
        return cycle

    def update(self, instance, validated_data):
        apt_ids = validated_data.pop('apartment_ids', None)
        cycle = super().update(instance, validated_data)
        if apt_ids is not None:
            from apps.buildings.models import Apartment
            apts = Apartment.objects.filter(
                id__in=apt_ids,
                tower__building=cycle.building,
            )
            cycle.apartments.set(apts)
        return cycle


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
