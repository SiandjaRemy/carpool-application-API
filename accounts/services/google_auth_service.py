import requests
import logging

from django.conf import settings
from django.contrib.auth import get_user_model

from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User

logger = logging.getLogger("app")
# User = get_user_model()


class GoogleAuthService:

    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    @classmethod
    def authenticate(cls, code: str, redirect_uri: str) -> dict:
        """
        Full Google OAuth flow.
        Returns JWT tokens + user data, raises on any failure.
        """
        access_token = cls._exchange_code(code, redirect_uri)
        user_info = cls._fetch_user_info(access_token)
        user = cls._get_or_create_user(user_info)
        return cls._build_response(user)

    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------

    @classmethod
    def _exchange_code(cls, code: str, redirect_uri: str) -> str:
        """Exchange Google auth code for an access token."""
        response = requests.post(
            cls.GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
                "client_secret": settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

        data = response.json()

        if "error" in data:
            logger.warning("Google token exchange failed: %s", data)
            raise ValueError(
                f"Google token exchange failed: {data.get('error_description', data['error'])}"
            )

        return data["access_token"]

    @classmethod
    def _fetch_user_info(cls, access_token: str) -> dict:
        """Fetch user profile from Google."""
        response = requests.get(
            cls.GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        data = response.json()

        if "error" in data:
            logger.warning("Google userinfo fetch failed: %s", data)
            raise ValueError("Failed to fetch user info from Google")

        return data

    @classmethod
    def _get_or_create_user(cls, user_info: dict) -> User:
        """Find existing user or create a new one from Google data."""
        email = user_info.get("email")
        first_name = user_info.get("given_name", "")
        last_name = user_info.get("family_name", "")

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": cls._unique_username(email),
                "first_name": first_name,
                "last_name": last_name,
                "is_active": True,
            },
        )

        if not created:
            # Intentionally do NOT call set_unusable_password() here.
            # The user may have registered with a password first.
            # Google auth is additive, its just to fill in missing name fields.
            cls._update_user_if_needed(user, first_name, last_name)
        if created:
            user.set_unusable_password()
            user.save()

        action = "created" if created else "authenticated"
        logger.info("User %s via Google OAuth: %s", action, email)

        return user

    @classmethod
    def _update_user_if_needed(
        cls, user: User, first_name: str, last_name: str
    ) -> None:
        """Fill in missing name fields for returning users."""
        updates = {}
        if not user.first_name and first_name:
            updates["first_name"] = first_name
        if not user.last_name and last_name:
            updates["last_name"] = last_name
        if updates:
            User.objects.filter(pk=user.pk).update(**updates)

    @classmethod
    def _unique_username(cls, email: str) -> str:
        """Generate a unique username from the email prefix."""
        base = email.split("@")[0]
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
        return username

    @classmethod
    def _build_response(cls, user: User) -> dict:
        """Issue JWT tokens and return the full auth payload."""
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
        }
