from rest_framework import serializers
from .models import User


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

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'role', 'is_active', 'date_joined',
            'assigned_apartment_ids',
        ]
        read_only_fields = ['id', 'date_joined']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=4)
    assigned_apartment_ids = _ApartmentIdField(
        source='assigned_apartments', many=True, required=False,
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'password', 'email', 'first_name', 'last_name',
            'phone', 'role', 'is_active', 'assigned_apartment_ids',
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
            'phone', 'role', 'is_active', 'password', 'assigned_apartment_ids',
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


class MeSerializer(serializers.ModelSerializer):
    """Read-only serializer for the authenticated user's own profile."""

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'role', 'is_active', 'date_joined',
        ]
