from rest_framework import viewsets
from apps.accounts.views import IsAdminUser
from .models import Building, Tower, Apartment
from .serializers import (
    BuildingSerializer, BuildingCreateSerializer,
    TowerSerializer, TowerCreateSerializer,
    ApartmentSerializer,
)


class BuildingViewSet(viewsets.ModelViewSet):
    queryset = Building.objects.prefetch_related('towers__apartments').all()
    permission_classes = [IsAdminUser]
    search_fields = ['name', 'address']
    ordering_fields = ['name', 'created_at']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return BuildingCreateSerializer
        return BuildingSerializer


class TowerViewSet(viewsets.ModelViewSet):
    queryset = Tower.objects.select_related('building').prefetch_related('apartments').all()
    permission_classes = [IsAdminUser]
    filterset_fields = ['building']
    search_fields = ['name']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return TowerCreateSerializer
        return TowerSerializer


class ApartmentViewSet(viewsets.ModelViewSet):
    queryset = Apartment.objects.select_related('tower__building').all()
    permission_classes = [IsAdminUser]
    serializer_class = ApartmentSerializer
    filterset_fields = ['tower', 'tower__building', 'floor']
    search_fields = ['number', 'meter_id']
