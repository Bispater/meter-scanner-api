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
