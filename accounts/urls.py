from django.urls import path, include


from accounts import views

app_name = "accounts"


urlpatterns = [
    path("google/", views.GoogleAuthView.as_view(), name="google-auth"),
    # path("", include("social_django.urls", namespace="social")),
    # path("", include("djoser.social.urls")),
    ############################
    # All the extra urls provided by djoser srent needed for this project so they were commented out
    # path("", include("djoser.urls")),
    path("", include("djoser.urls.jwt")),
    path("users/", views.UserCreateAPIView.as_view(), name="register"),
    path("users/me/", views.UserView.as_view(), name="user-me"),
    path("users/me/logout/", views.LogoutView.as_view()),
    path(
        "users/set_password/",
        views.PasswordChangeView.as_view(),
        name="user-set-password",
    ),
    path(
        "users/reset_password/",
        views.PasswordResetView.as_view(),
        name="user-reset-password",
    ),
    path(
        "users/reset_password_confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="user-reset-password-confirm",
    ),
    path("test/google-auth/", views.google_auth_test, name="google-auth-test"),
]
