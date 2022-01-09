from django.utils import timezone
from rest_framework import serializers

from core.models import LaunchedApp, Session


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = '__all__'


class LaunchedAppSerializer(serializers.ModelSerializer):
    session = SessionSerializer(source='created_by')

    class Meta:
        model = LaunchedApp
        fields = (
            'session', 'app_name', 'url',
            'status', 'status_updated_at', 'launched_at'
        )


class AppRequestSerializer(serializers.Serializer):
    app = serializers.ChoiceField(choices=Session.get_valid_apps())
    session_id = serializers.UUIDField(required=False)

    def validate_session_id(self, session_id):
        session = Session.objects.get_or_none(id=session_id)
        if session:
            if session.expires_at < timezone.now():
                raise serializers.ValidationError(f"Your session '{session_id}' has expired.")
        else:
            raise serializers.ValidationError(f"Invalid session identifier '{session_id}'.")

        return session_id
