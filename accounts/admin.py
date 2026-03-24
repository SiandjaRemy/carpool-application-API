from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from accounts.models import User


class UserAdmin(admin.ModelAdmin):

    form = UserChangeForm
    add_form = UserCreationForm
    # Setting this to false removes the extra count query
    show_full_result_count = False
    list_display = ["email", "username", "first_name", "last_name"]

    # Show a clear read-only indicator for OAuth users
    readonly_fields = ("password_display", "date_joined", "last_login")

    def password_display(self, obj):
        if not obj.has_usable_password():
            return "⛔ OAuth account — no password set"
        return "Password set (hashed)"

    password_display.short_description = "Password status"

    # Replace the raw password field with your safe read-only version
    fieldsets = (
        (None, {"fields": ("email", "username", "password_display")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )


admin.site.register(User, UserAdmin)
