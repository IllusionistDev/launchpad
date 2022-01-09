
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from core.models import Session

from .serializers import (
    AppRequestSerializer,
    LaunchedAppSerializer,
)


class ListAppsAPIView(views.APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response(data=Session.get_valid_apps(), status=status.HTTP_200_OK)


class LaunchAppAPIView(views.APIView):
    permission_classes = (AllowAny,)
    serializer_class = AppRequestSerializer

    def post(self, request):
        """
        Launches an app session
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        launched_app = Session.install_app(
            app_name=serializer.data['app'],
            session_id=serializer.data['session_id'],
        )
        return Response(
            data=LaunchedAppSerializer(launched_app).data,
            status=status.HTTP_200_OK
        )


class UninstallAppAPIView(views.APIView):
    permission_classes = (AllowAny,)
    serializer_class = AppRequestSerializer

    def post(self, request):
        """
        Uninstall an app from session
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        if session_id := serializer.data['session_id']:
            Session.uninstall(
                app_name=serializer.data['app'],
                session_id=session_id,
            )
        return Response(
            data={
                'success': True,
                'message': f"{serializer.data['app']} has been uninstalled successfully.",
                'session': session_id
            },
            status=status.HTTP_200_OK
        )
