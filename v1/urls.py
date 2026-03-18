from django.urls import path, include

app_name = "v1"

# Import directly from your existing app URLs
urlpatterns = [
    # All auth endpoints under v1/auth/
    path("auth/", include(("accounts.urls", "accounts"), namespace="auth")),
    # All carpool endpoints under v1/carpool/
    path("carpool/", include(("carpool.urls", "carpool"), namespace="carpool")),
]
