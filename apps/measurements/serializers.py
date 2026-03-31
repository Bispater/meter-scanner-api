from rest_framework import serializers
from .models import Measurement


class MeasurementSerializer(serializers.ModelSerializer):
    tower_name = serializers.CharField(source='apartment.tower.name', read_only=True)
    building_name = serializers.CharField(source='apartment.tower.building.name', read_only=True)
    apartment_number = serializers.CharField(source='apartment.number', read_only=True)
    meter_id = serializers.CharField(source='apartment.meter_id', read_only=True)
    operator_name = serializers.SerializerMethodField()

    class Meta:
        model = Measurement
        fields = [
            'id', 'apartment', 'operator', 'reading_value', 'unit',
            'photo', 'status', 'meter_type',
            'latitude', 'longitude',
            'captured_at', 'created_at',
            # Read-only enriched fields
            'tower_name', 'building_name', 'apartment_number', 'meter_id',
            'operator_name',
        ]
        read_only_fields = ['id', 'created_at']

    def get_operator_name(self, obj):
        if obj.operator:
            return obj.operator.get_full_name() or obj.operator.username
        return None


class MeasurementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = [
            'id', 'apartment', 'reading_value', 'unit',
            'photo', 'status', 'meter_type',
            'latitude', 'longitude', 'captured_at',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        # Auto-assign the authenticated user as operator
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['operator'] = request.user
        return super().create(validated_data)
