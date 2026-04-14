from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from apps.accounts.views import IsAdminUser
from .models import Building, Tower, Apartment
from .serializers import (
    BuildingSerializer, BuildingCreateSerializer,
    TowerSerializer, TowerCreateSerializer,
    ApartmentSerializer, BulkApartmentSerializer,
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

    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create_apartments(self, request):
        serializer = BulkApartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tower = serializer.validated_data['tower']
        items = serializer.validated_data['apartments']

        objs = [
            Apartment(tower=tower, number=a['number'], floor=a['floor'], meter_id=a['meter_id'])
            for a in items
        ]

        with transaction.atomic():
            created = Apartment.objects.bulk_create(objs, ignore_conflicts=False)

        out = ApartmentSerializer(created, many=True)
        return Response({'created': len(created), 'apartments': out.data}, status=status.HTTP_201_CREATED)
