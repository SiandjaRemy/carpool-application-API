from datetime import timedelta
import logging

from django.db import transaction
from django.utils import timezone

from carpool.exceptions import BusinessValidationError, ResourcePermissionError
from carpool.models import Ride, RideRequest
from carpool.enums.enums import RequestStatus, ReservationPaymentStatus, RideStatus

from carpool.models.reservation import Reservation
from carpool.send_emails import alert_a_user_via_email
from carpool.services.request_service import RideRequestService

celery_logger = logging.getLogger("celery")


class RideService:
    """Service layer for ride business logic"""

    @staticmethod
    def _validate_ride_state(ride):
        """
        Validates the overall state of a Ride object,
        whether newly created or recently updated.
        """
        if ride.status != RideStatus.SCHEDULED:
            raise BusinessValidationError(f"Cannot modify a ride that is {ride.status}")

        if ride.departure_datetime <= timezone.now():
            raise BusinessValidationError("Departure time must be in the future")

        if ride.available_seats <= 0:
            raise BusinessValidationError("A ride must have at least 1 available seat")

        if ride.price_per_seat < 0:
            raise BusinessValidationError("Price per seat cannot be negative")

        query = Ride.objects.filter(
            user=ride.user,
            status=RideStatus.SCHEDULED,
            departure_datetime__range=(
                ride.departure_datetime - timedelta(hours=2),
                ride.departure_datetime + timedelta(hours=2),
            ),
        )

        if ride.pk:
            query = query.exclude(pk=ride.pk)

        if query.exists():
            raise BusinessValidationError("Schedule conflict detected.")

    @classmethod
    @transaction.atomic
    def create_ride(cls, ride_data, user):
        # Create instance in memory only (does not hit DB yet)
        ride = Ride(**ride_data, user=user)

        # Validate the state of this new object
        cls._validate_ride_state(ride)

        # Now save to DB
        ride.save()
        return ride

    @classmethod
    @transaction.atomic
    def update_ride(cls, ride_id, update_data, user):
        """
        Update an existing ride with row-level locking.
        """

        # 1. Fetch and Lock the ride
        instance = Ride.objects.select_for_update().get(id=ride_id, user=user)

        # Apply updates to the instance in memory
        for field, value in update_data.items():
            setattr(instance, field, value)

        # Validate the FINAL state of the object
        cls._validate_ride_state(instance)

        # Save
        instance.save(update_fields=list(update_data.keys()) + ["updated_at"])

        return instance

    @classmethod
    @transaction.atomic
    def cancel_ride(cls, ride_id, user):
        """
        Cancel a scheduled ride
        """
        ride = (
            Ride.objects.select_for_update()
            .select_related("user")
            .get(id=ride_id, status=RideStatus.SCHEDULED)
        )

        # Specific Permission Error
        if ride.user != user:
            raise ResourcePermissionError(
                "You do not have permission to cancel this ride."
            )

        # Auto cancel all ride requests if they exist
        RideRequestService.cancel_ride_requests(ride_id=ride_id)

        ride.status = RideStatus.CANCELLED
        ride.save(update_fields=["status", "updated_at"])

        # Notify passengers (if any)
        # from carpool.tasks import notify_ride_cancelled
        # transaction.on_commit(
        #     lambda: notify_ride_cancelled.delay(ride.id)
        # )

        return ride

    @classmethod
    def check_seat_availability(cls, ride_id, requested_seats):
        """
        Check if requested seats are available
        """
        try:
            ride = Ride.objects.get(id=ride_id)
            return ride.available_seats >= requested_seats
        except Ride.DoesNotExist:
            return False


class RideBatchService:
    """System-level operations for carpool maintenance and notifications."""

    # --- SCHEDULED MAINTENANCE TASKS ---

    @classmethod
    @transaction.atomic
    def auto_start_rides(cls):
        """
        Transition SCHEDULED -> IN_PROGRESS 10 mins before departure.
        Also expires any lingering PENDING requests for these rides.
        """
        threshold = timezone.now() + timedelta(minutes=10)

        rides_starting = Ride.objects.select_for_update().filter(
            status=RideStatus.SCHEDULED, departure_datetime__lte=threshold
        )

        # 1. Update Ride Status
        count = rides_starting.update(
            status=RideStatus.IN_PROGRESS, updated_at=timezone.now()
        )

        # 2. Expire PENDING requests (Atomic cascade)
        RideRequest.objects.filter(
            ride__in=rides_starting, status=RequestStatus.PENDING
        ).update(status=RequestStatus.EXPIRED, updated_at=timezone.now())

        return f"Started {count} rides and expired associated pending requests."

    @classmethod
    @transaction.atomic
    def auto_start_rides_2(cls):
        # Calculate threshold time (10 minutes from now)
        threshold_time = timezone.now() + timedelta(minutes=10)

        # Get rides with status SCHEDULED AND departure time <= threshold
        upcoming_rides = (
            Ride.objects.select_related("user")
            .filter(status=RideStatus.SCHEDULED, departure_datetime__lte=threshold_time)
            .order_by("-created_at")
        )

        if upcoming_rides.exists():
            id_list = [ride.id for ride in upcoming_rides]
            # Update rides in bulk
            Ride.objects.filter(id__in=id_list).update()

            # Send emails for this expired_rides
            for ride in upcoming_rides:
                subject = f"Your ride from {ride.departure_town} to {ride.arrival_town} is approaching"
                message = (
                    f"Hey {ride.user.username},\n\n"
                    f"This is a reminder that your ride from {ride.departure_town} "
                    f"to {ride.arrival_town} is scheduled to depart within the next 10 minutes.\n\n"
                    f"Departure Town: {ride.departure_town}\n"
                    f"Arrival Town: {ride.arrival_town}\n"
                    f"Departure Time: {ride.departure_datetime.strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"The ride will be marked as inactive shortly."
                )

                try:
                    # Comment when working offline
                    alert_a_user_via_email(
                        email=ride.user.email, subject=subject, message=message
                    )
                    print(message)
                except Exception as e:
                    celery_logger.error(
                        f"Failed to send notification for ride {ride.id}: {str(e)}"
                    )

        else:
            return "No expired rides found"

        return f"Deactivated {len(upcoming_rides)} expired rides"

    @classmethod
    def auto_expire_past_rides(cls):
        """Clean up rides that never started or were forgotten."""
        count = Ride.objects.filter(
            status=RideStatus.SCHEDULED, departure_datetime__lt=timezone.now()
        ).update(status=RideStatus.EXPIRED, updated_at=timezone.now())
        return f"Expired {count} stale rides."

    # --- NOTIFICATION & REMINDER TASKS ---

    @classmethod
    def send_departure_reminders(cls):
        """
        Remind passengers of SCHEDULED rides departing in 30-60 mins.
        Uses prefetched reservations to reach the final passenger list.
        """
        now = timezone.now()
        window_start, window_end = now + timedelta(minutes=30), now + timedelta(
            minutes=60
        )

        upcoming_rides = Ride.objects.filter(
            status=RideStatus.SCHEDULED,
            departure_datetime__range=(window_start, window_end),
            departure_reminder_sent=False,  # I still recommend a DB field!
        ).prefetch_related("reservations__passenger")

        for ride in upcoming_rides:
            passengers = [res.passenger for res in ride.reservations.all()]
            # Trigger notification logic here (e.g., Firebase/SMS)
            # task_bulk_notify.delay(passengers, "Your ride departs soon!")

        upcoming_rides.update(departure_reminder_sent=True)
        return f"Departure reminders sent for {upcoming_rides.count()} rides."

    @classmethod
    def remind_unpaid_reservations(cls):
        """
        Find unpaid reservations 2-3 hours before departure.
        """
        now = timezone.now()
        window_start, window_end = now + timedelta(hours=2), now + timedelta(hours=3)

        unpaid_reservations = Reservation.objects.filter(
            ride__departure_datetime__range=(window_start, window_end),
            ride__status=RideStatus.SCHEDULED,
            payment_status=ReservationPaymentStatus.PAYMENT_DISABLED,
        ).select_related("passenger", "ride")

        for res in unpaid_reservations:
            # task_notify_payment_required.delay(res.passenger.id, res.ride.id)
            pass

        return f"Payment reminders sent for {unpaid_reservations.count()} reservations."

    @classmethod
    def request_review_reminders(cls):
        """
        Triggered for rides that COMPLETED 2 hours ago.
        Requires 'arrival_datetime' or an estimation logic.
        """
        two_hours_ago = timezone.now() - timedelta(hours=2)

        # Only remind users who haven't been asked yet
        completed_rides = Ride.objects.filter(
            status=RideStatus.COMPLETED,
            updated_at__lte=two_hours_ago,
            review_reminder_sent=False,
        ).prefetch_related("reservations__passenger")

        for ride in completed_rides:
            # Notify driver about passengers, notify passengers about driver
            pass

        completed_rides.update(review_reminder_sent=True)
        return f"Review prompts queued for {completed_rides.count()} rides."

    # --- ONE-OFF ASYNC TASKS (Triggered via API/View) ---

    @classmethod
    def notify_ride_cancellation(cls, ride_id):
        """One-off: Notify all involved parties when a driver cancels."""
        ride = Ride.objects.prefetch_related("reservations__passenger").get(id=ride_id)

        recipients = [res.passenger for res in ride.reservations.all()]
        # task_send_cancellation_email.delay(recipients, ride_id)

        celery_logger.info(f"Cancellation notifications queued for ride {ride_id}")
