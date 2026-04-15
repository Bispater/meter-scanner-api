from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from apps.accounts.views import IsAdminUser, _managed_org_ids
from .models import Building, Tower, Apartment
from .serializers import (
    BuildingSerializer, BuildingCreateSerializer,
    TowerSerializer, TowerCreateSerializer,
    ApartmentSerializer, BulkApartmentSerializer,
)


class BuildingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    search_fields = ['name', 'address']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        org_ids = _managed_org_ids(self.request.user)
        qs = Building.objects.prefetch_related('towers__apartments')
        if org_ids is None:
            return qs.all()
        return qs.filter(organization_id__in=org_ids)

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return BuildingCreateSerializer
        return BuildingSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if not serializer.validated_data.get('organization'):
            serializer.save(organization=user.organization)
        else:
            serializer.save()


class TowerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    filterset_fields = ['building']
    search_fields = ['name']

    def get_queryset(self):
        org_ids = _managed_org_ids(self.request.user)
        qs = Tower.objects.select_related('building').prefetch_related('apartments')
        if org_ids is None:
            return qs.all()
        return qs.filter(building__organization_id__in=org_ids)

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return TowerCreateSerializer
        return TowerSerializer


class ApartmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = ApartmentSerializer
    filterset_fields = ['tower', 'tower__building', 'floor']
    search_fields = ['number', 'meter_id', 'qr_code']

    def get_queryset(self):
        org_ids = _managed_org_ids(self.request.user)
        qs = Apartment.objects.select_related('tower__building')
        if org_ids is None:
            return qs.all()
        return qs.filter(tower__building__organization_id__in=org_ids)

    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create_apartments(self, request):
        serializer = BulkApartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tower = serializer.validated_data['tower']
        items = serializer.validated_data['apartments']

        with transaction.atomic():
            created = []
            for a in items:
                obj = Apartment(
                    tower=tower,
                    number=a['number'],
                    floor=a['floor'],
                    meter_id=a.get('meter_id', ''),
                    reading_layout=a.get('reading_layout', Apartment.ReadingLayout.A),
                )
                obj.save()  # triggers qr_code auto-generation
                created.append(obj)

        out = ApartmentSerializer(created, many=True)
        return Response({'created': len(created), 'apartments': out.data}, status=status.HTTP_201_CREATED)
