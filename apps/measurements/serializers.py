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

    class Meta:
        model = Measurement
        fields = [
            'id', 'apartment', 'operator', 'reading_value', 'ocr_value',
            'modified_by_user', 'unit',
            'photo', 'photo_url', 'status', 'meter_type',
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

        return attrs

    def create(self, validated_data):
        # Auto-assign the authenticated user as operator
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['operator'] = request.user
        return super().create(validated_data)
