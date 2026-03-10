from django.contrib import admin

# Register your models here.

from reservations.models import Reservation


admin.site.register(Reservation)
