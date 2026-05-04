from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Notificaciones del usuario autenticado.

    GET /api/notifications/                      → lista
    GET /api/notifications/unread_count/         → conteo no leídas
    POST /api/notifications/{id}/mark_read/      → marcar una
    POST /api/notifications/mark_all_read/       → marcar todas
    DELETE /api/notifications/{id}/              → borrar una
    """

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user).select_related('measurement')
        unread = self.request.query_params.get('unread')
        if unread in ('1', 'true', 'True'):
            qs = qs.filter(is_read=False)
        return qs

    @action(detail=False, methods=['get'], url_path='unread_count')
    def unread_count(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'count': count})

    @action(detail=True, methods=['post'], url_path='mark_read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])
        ser = self.get_serializer(notification)
        return Response(ser.data)

    @action(detail=False, methods=['post'], url_path='mark_all_read')
    def mark_all_read(self, request):
        updated = Notification.objects.filter(
            recipient=request.user, is_read=False,
        ).update(is_read=True, read_at=timezone.now())
        return Response({'updated': updated}, status=status.HTTP_200_OK)
