from rest_framework import serializers
from .models import User, Organization


class OrganizationSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(source='members.count', read_only=True)
    building_count = serializers.IntegerField(source='buildings.count', read_only=True)

    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'created_at', 'member_count', 'building_count']
        read_only_fields = ['id', 'created_at']


def _apartment_queryset():
    from apps.buildings.models import Apartment
    return Apartment.objects.all()


class _ApartmentIdField(serializers.PrimaryKeyRelatedField):
    """Lazy queryset to avoid circular import at class-definition time."""
    def get_queryset(self):
        return _apartment_queryset()


class UserSerializer(serializers.ModelSerializer):
    assigned_apartment_ids = _ApartmentIdField(
        source='assigned_apartments', many=True, required=False,
    )
    organization_name = serializers.CharField(source='organization.name', read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'role', 'is_active', 'date_joined',
            'organization', 'organization_name',
            'assigned_apartment_ids',
        ]
        read_only_fields = ['id', 'date_joined', 'organization_name']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=4)
    assigned_apartment_ids = _ApartmentIdField(
        source='assigned_apartments', many=True, required=False,
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'password', 'email', 'first_name', 'last_name',
            'phone', 'role', 'is_active', 'organization', 'assigned_apartment_ids',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        apartments = validated_data.pop('assigned_apartments', [])
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if apartments:
            user.assigned_apartments.set(apartments)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=4, required=False)
    assigned_apartment_ids = _ApartmentIdField(
        source='assigned_apartments', many=True, required=False,
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'role', 'is_active', 'password', 'organization', 'assigned_apartment_ids',
        ]
        read_only_fields = ['id']

    def update(self, instance, validated_data):
        apartments = validated_data.pop('assigned_apartments', None)
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        if apartments is not None:
            instance.assigned_apartments.set(apartments)
        return instance


class AssignedApartmentSerializer(serializers.Serializer):
    """Lightweight serializer for assigned apartments (used in /me endpoint)."""
    id = serializers.IntegerField()
    meter_id = serializers.CharField()
    qr_code = serializers.CharField()
    number = serializers.CharField()
    floor = serializers.IntegerField()
    tower_name = serializers.CharField(source='tower.name')
    building_name = serializers.CharField(source='tower.building.name')
    apartment_info = serializers.SerializerMethodField()
    qr_data = serializers.SerializerMethodField()

    def get_apartment_info(self, obj):
        return f'{obj.tower.name} — Depto {obj.number}'

    def get_qr_data(self, obj):
        import json
        return json.dumps({
            'qr_code': obj.qr_code,
            'apartment_info': f'{obj.tower.name} — Depto {obj.number}',
            'apartment_id': obj.id,
        })


class MeSerializer(serializers.ModelSerializer):
    """Read-only serializer for the authenticated user's own profile."""
    assigned_apartments = AssignedApartmentSerializer(many=True, read_only=True)
    organization_id = serializers.IntegerField(source='organization.id', read_only=True, default=None)
    organization_name = serializers.CharField(source='organization.name', read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'role', 'is_active', 'date_joined',
            'organization_id', 'organization_name',
            'assigned_apartments',
        ]
