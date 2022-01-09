from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny

schema_view = get_schema_view(
    openapi.Info(
        title="Launchpad API",
        default_version='v1',
        description="Launchpad API Schema",
    ),
    public=True,
    permission_classes=(AllowAny,)
)

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin/', admin.site.urls),
    path(
        'api/v1/',
        include([
            path('launchpad/', include(('core.api.v1.urls', 'launchpad'), namespace='launchpad-v1')),
        ]),
    ),
    path('swagger/', schema_view.with_ui('swagger'), name='schema-swagger-ui'),
    path('__debug__/', include('debug_toolbar.urls')),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
