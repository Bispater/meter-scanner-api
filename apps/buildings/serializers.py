from rest_framework import serializers
from .models import Building, Tower, Apartment


class ApartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Apartment
        fields = ['id', 'number', 'floor', 'meter_id', 'tower']
        read_only_fields = ['id']


class TowerSerializer(serializers.ModelSerializer):
    apartments = ApartmentSerializer(many=True, read_only=True)
    apartment_count = serializers.IntegerField(source='apartments.count', read_only=True)

    class Meta:
        model = Tower
        fields = ['id', 'name', 'building', 'apartments', 'apartment_count']
        read_only_fields = ['id']


class TowerCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tower
        fields = ['id', 'name', 'building']
        read_only_fields = ['id']


class BulkApartmentItemSerializer(serializers.Serializer):
    number = serializers.CharField(max_length=20)
    floor = serializers.IntegerField(default=1)
    meter_id = serializers.CharField(max_length=50)


class BulkApartmentSerializer(serializers.Serializer):
    tower = serializers.PrimaryKeyRelatedField(queryset=Tower.objects.all())
    apartments = BulkApartmentItemSerializer(many=True)

    def validate_apartments(self, value):
        if not value:
            raise serializers.ValidationError("Debe incluir al menos un departamento.")
        if len(value) > 1000:
            raise serializers.ValidationError("Máximo 1000 departamentos por solicitud.")
        return value


class BuildingSerializer(serializers.ModelSerializer):
    towers = TowerSerializer(many=True, read_only=True)
    tower_count = serializers.IntegerField(source='towers.count', read_only=True)
    apartment_count = serializers.SerializerMethodField()

    class Meta:
        model = Building
        fields = ['id', 'name', 'address', 'created_at', 'towers', 'tower_count', 'apartment_count']
        read_only_fields = ['id', 'created_at']

    def get_apartment_count(self, obj):
        return Apartment.objects.filter(tower__building=obj).count()


class BuildingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = ['id', 'name', 'address']
        read_only_fields = ['id']
