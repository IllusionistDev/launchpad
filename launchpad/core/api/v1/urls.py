
from django.urls import path

from .views import ListAppsAPIView, LaunchAppAPIView, UninstallAppAPIView

urlpatterns = [
    path('app/list/', ListAppsAPIView.as_view()),
    path('app/launch/', LaunchAppAPIView.as_view()),
    path('app/uninstall/', UninstallAppAPIView.as_view())
]
