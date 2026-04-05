from celery import shared_task
from carpool.services.ride_service import RideBatchService


@shared_task
def task_auto_start_rides():
    result = RideBatchService.auto_start_rides()
    return result


@shared_task
def task_auto_ride_departure_reminder():
    result = RideBatchService.send_departure_reminders()
    return result


@shared_task
def task_auto_remind_unpaid_reservations():
    result = RideBatchService.remind_unpaid_reservations()
    return result


@shared_task
def task_auto_request_reviews():
    result = RideBatchService.request_review_reminders()
    return result
