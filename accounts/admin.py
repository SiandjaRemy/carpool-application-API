from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.db.models import Q

from accounts.models import User



class UserAdmin(admin.ModelAdmin):
    # Setting this to false removes the extra count query
    show_full_result_count = False
    list_display = ["email", "username", "first_name", "last_name"]

    


admin.site.register(User, UserAdmin)


