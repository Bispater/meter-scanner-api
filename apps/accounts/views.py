from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer, UserCreateSerializer, UserUpdateSerializer, MeSerializer


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'


class UserViewSet(viewsets.ModelViewSet):
    """CRUD for users. Only admins can manage users."""
    queryset = User.objects.all()
    permission_classes = [IsAdminUser]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['date_joined', 'username']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UserUpdateSerializer
        return UserSerializer

    @action(detail=True, methods=['post'], url_path='assign-apartments')
    def assign_apartments(self, request, pk=None):
        """POST list of apartment IDs to assign to this user."""
        user = self.get_object()
        apartment_ids = request.data.get('apartment_ids', [])
        from apps.buildings.models import Apartment
        apartments = Apartment.objects.filter(id__in=apartment_ids)
        user.assigned_apartments.set(apartments)
        return Response({'assigned': list(user.assigned_apartments.values_list('id', flat=True))})

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='me')
    def me(self, request):
        """Get current authenticated user profile with assigned apartments."""
        user = User.objects.prefetch_related(
            'assigned_apartments__tower__building',
        ).get(pk=request.user.pk)
        serializer = MeSerializer(user)
        return Response(serializer.data)
