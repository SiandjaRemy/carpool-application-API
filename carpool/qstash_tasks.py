from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from qstash import Receiver

from django.conf import settings

from carpool.services.ride_service import RideBatchService

receiver = Receiver(
    current_signing_key=settings.QSTASH_CURRENT_SIGNING_KEY,
    next_signing_key=settings.QSTASH_NEXT_SIGNING_KEY,
)


@method_decorator(csrf_exempt, name="dispatch")
class QStashTaskView(View):
    def post(self, request, task_name, *args, **kwargs):
        # 1. Verify the request actually came from Upstash QStash
        signature = request.headers.get("Upstash-Signature")
        try:
            receiver.verify(body=request.body.decode("utf-8"), signature=signature)
        except Exception:
            return JsonResponse({"error": "Invalid signature"}, status=401)

        # 2. Route the request to the correct service
        # Ride Scheduled tasks
        if task_name == "auto-start-rides":
            result = RideBatchService.auto_start_rides()
        elif task_name == "departure-reminders":
            result = RideBatchService.send_departure_reminders()
        elif task_name == "unpaid-reservations":
            result = RideBatchService.remind_unpaid_reservations()
        elif task_name == "request-reviews":
            result = RideBatchService.request_review_reminders()
        else:
            return JsonResponse({"error": "Unknown task"}, status=404)

        return JsonResponse({"status": "success", "result": result})
