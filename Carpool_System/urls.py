from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import handler404, handler500
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
    openapi.Info(
        title="Carpool Application API",
        default_version="v1",
        description="An API for a carpool system",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="remysiandja@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)


api_patterns = [
    path("auth/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("carpool/", include(("carpool.urls", "carpool"), namespace="carpool")),
]


urlpatterns = [
    # swagger
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    re_path(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    re_path(
        r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
    path("admin/", admin.site.urls),
    path("api/", include((api_patterns))),
    # path("api/", include(api_patterns)),
]

# ONLY include debug toolbar urls if it's actually in INSTALLED_APPS
if "debug_toolbar" in settings.INSTALLED_APPS:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
