from django.contrib import admin

from rides_and_requests.models import Ride, RideAlert, RideRequest


admin.site.register(Ride)
admin.site.register(RideRequest)
admin.site.register(RideAlert)