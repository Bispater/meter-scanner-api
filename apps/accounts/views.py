from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User, Organization
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer, MeSerializer,
    OrganizationSerializer,
)


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'


def _managed_org_ids(user):
    """Returns a set of organization IDs this admin can manage. None = all (superuser)."""
    if user.is_superuser:
        return None
    ids = set()
    if user.organization_id:
        ids.add(user.organization_id)
    ids.update(user.extra_organizations.values_list('id', flat=True))
    return ids


class OrganizationViewSet(viewsets.ModelViewSet):
    """CRUD for organizations. Superusers see all; admins see only their orgs."""
    serializer_class = OrganizationSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        user = self.request.user
        org_ids = _managed_org_ids(user)
        if org_ids is None:
            return Organization.objects.all()
        return Organization.objects.filter(id__in=org_ids)

    def perform_create(self, serializer):
        org = serializer.save()
        # Add org to the creating admin's extra_organizations if not their primary
        user = self.request.user
        if user.organization_id != org.id:
            user.extra_organizations.add(org)


class UserViewSet(viewsets.ModelViewSet):
    """CRUD for users. Admins can only manage users in their org(s)."""
    permission_classes = [IsAdminUser]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['date_joined', 'username']

    def get_queryset(self):
        org_ids = _managed_org_ids(self.request.user)
        if org_ids is None:
            return User.objects.all()
        return User.objects.filter(organization_id__in=org_ids)

    def perform_create(self, serializer):
        user = self.request.user
        if not serializer.validated_data.get('organization'):
            serializer.save(organization=user.organization)
        else:
            serializer.save()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UserUpdateSerializer
        return UserSerializer

    @action(detail=True, methods=['post'], url_path='assign-apartments')
    def assign_apartments(self, request, pk=None):
        """POST list of apartment IDs to assign to this user.
        
        Apartments that have at least one verified measurement from this operator
        cannot be removed from the assignment.
        """
        user = self.get_object()
        apartment_ids = set(int(i) for i in request.data.get('apartment_ids', []))

        from apps.buildings.models import Apartment
        from apps.measurements.models import Measurement

        # Find currently assigned apartments that have verified measurements
        # from this operator — these are protected and cannot be removed.
        protected_ids = set(
            Measurement.objects.filter(
                operator=user,
                status='verified',
                apartment__in=user.assigned_apartments.all(),
            ).values_list('apartment_id', flat=True).distinct()
        )

        # Always keep protected apartments regardless of what was submitted
        final_ids = apartment_ids | protected_ids

        apartments = Apartment.objects.filter(id__in=final_ids)
        user.assigned_apartments.set(apartments)

        removed_protected = protected_ids - apartment_ids
        response_data = {
            'assigned': list(user.assigned_apartments.values_list('id', flat=True)),
        }
        if removed_protected:
            response_data['warning'] = (
                f'{len(removed_protected)} departamento(s) no pudieron ser removidos '
                'porque tienen mediciones verificadas asociadas.'
            )
            response_data['protected_ids'] = list(removed_protected)

        return Response(response_data)

    @action(detail=True, methods=['get'], url_path='protected-apartments')
    def protected_apartments(self, request, pk=None):
        """Return apartment IDs that cannot be unassigned (have verified measurements)."""
        user = self.get_object()
        from apps.measurements.models import Measurement
        protected = list(
            Measurement.objects.filter(
                operator=user,
                status='verified',
            ).values_list('apartment_id', flat=True).distinct()
        )
        return Response({'protected_apartment_ids': protected})

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='me')
    def me(self, request):
        """Get current authenticated user profile with assigned apartments and active cycle info."""
        from apps.cycles.models import MeasurementCycle
        from apps.measurements.models import Measurement

        user = User.objects.prefetch_related(
            'assigned_apartments__tower__building',
        ).get(pk=request.user.pk)
        serializer = MeSerializer(user)
        data = serializer.data

        # Attach current active cycle per building that the operator has assignments in
        building_ids = set(
            user.assigned_apartments.values_list('tower__building_id', flat=True)
        )
        active_cycles = MeasurementCycle.objects.filter(
            building_id__in=building_ids,
            status__in=['pending', 'in_progress'],
        ).select_related('building').order_by('-year', '-month')

        cycles_data = []
        for cycle in active_cycles:
            # Apartments in this building assigned to the user
            user_apts = user.assigned_apartments.filter(tower__building=cycle.building)
            total = user_apts.count()

            # Which of those have been measured in this cycle window
            measured_ids = set(
                Measurement.objects.filter(
                    apartment__in=user_apts,
                    captured_at__date__gte=cycle.scheduled_date,
                    captured_at__date__lte=cycle.deadline,
                ).values_list('apartment_id', flat=True).distinct()
            )

            pending_apts = [
                {
                    'id': apt.id,
                    'meter_id': apt.meter_id,
                    'qr_code': apt.qr_code,
                    'number': apt.number,
                    'floor': apt.floor,
                    'tower_name': apt.tower.name,
                    'building_name': apt.tower.building.name,
                    'apartment_info': f'{apt.tower.name} — Depto {apt.number}',
                }
                for apt in user_apts.select_related('tower__building')
                if apt.id not in measured_ids
            ]

            cycles_data.append({
                'id': cycle.id,
                'name': cycle.name,
                'building_id': cycle.building_id,
                'building_name': cycle.building.name,
                'year': cycle.year,
                'month': cycle.month,
                'month_name': cycle.month_name,
                'scheduled_date': str(cycle.scheduled_date),
                'deadline': str(cycle.deadline),
                'status': cycle.status,
                'total_assigned': total,
                'measured_count': len(measured_ids),
                'pending_count': total - len(measured_ids),
                'pending_apartments': pending_apts,
            })

        data['active_cycles'] = cycles_data
        return Response(data)
