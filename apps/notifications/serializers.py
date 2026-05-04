from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    measurement_id = serializers.IntegerField(source='measurement.id', read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'title', 'body', 'payload',
            'is_read', 'created_at', 'read_at',
            'measurement_id',
        ]
        read_only_fields = fields
