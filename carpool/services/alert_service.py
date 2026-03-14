import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from carpool.models import RideAlert, Ride
from carpool.enums.enums import RideStatus


class RideAlertService:
    """Service layer for ride alert business logic"""

    @staticmethod
    def _validate_alert_dates(before_date, after_date) -> None:
        """Validate that dates are logical"""
        if before_date < after_date:
            raise ValueError("Before date must be after after date")

        if before_date <= timezone.now():
            raise ValueError("Before date must be in the future")

        if after_date <= timezone.now():
            raise ValueError("After date must be in the future")

    @classmethod
    @transaction.atomic
    def create_alert(cls, user, departure_town, arrival_town, before_date, after_date):
        """
        Create a new ride alert for a user
        """
        # Validate dates
        cls._validate_alert_dates(before_date, after_date)

        # Check for duplicate active alerts
        existing_alert = RideAlert.objects.filter(
            user=user,
            departure_town__iexact=departure_town,
            arrival_town__iexact=arrival_town,
            is_active=True,
        ).first()

        if existing_alert:
            raise ValueError(
                f"You already have an active alert for {departure_town} → {arrival_town}"
            )

        # Create alert
        alert = RideAlert.objects.create(
            user=user,
            departure_town=departure_town,
            arrival_town=arrival_town,
            before_date=before_date,
            after_date=after_date,
        )

        # Immediately check for matching rides
        cls._check_alert_matches(alert)

        return alert

    @classmethod
    @transaction.atomic
    def update_alert(cls, alert_id: uuid.UUID, user, **kwargs):
        """
        Update an existing alert
        """
        try:
            alert = RideAlert.objects.select_for_update().get(id=alert_id, user=user)
        except RideAlert.DoesNotExist:
            raise ValueError("Alert not found or you don't have permission")

        # Validate dates if they're being updated
        before_date = kwargs.get("before_date", alert.before_date)
        after_date = kwargs.get("after_date", alert.after_date)
        cls._validate_alert_dates(before_date, after_date)

        # Update fields
        for field, value in kwargs.items():
            if hasattr(alert, field):
                setattr(alert, field, value)

        alert.save(update_fields=list(kwargs.keys()) + ["updated_at"])

        # Check matches if route changed
        if "departure_town" in kwargs or "arrival_town" in kwargs:
            cls._check_alert_matches(alert)

        return alert

    @classmethod
    @transaction.atomic
    def toggle_alert(cls, alert_id: uuid.UUID, user):
        """
        Toggle alert active status
        """
        try:
            alert = RideAlert.objects.select_for_update().get(id=alert_id, user=user)
        except RideAlert.DoesNotExist:
            raise ValueError("Alert not found")

        alert.is_active = not alert.is_active
        alert.save(update_fields=["is_active", "updated_at"])

        return alert

    @classmethod
    def find_matching_rides(cls, alert: RideAlert):
        """
        Find rides that match an alert
        """
        queryset = Ride.objects.filter(
            departure_town__iexact=alert.departure_town,
            arrival_town__iexact=alert.arrival_town,
            status=RideStatus.SCHEDULED,
            departure_datetime__gte=timezone.now(),
            available_seats__gt=0,
            is_active=True,
        )

        # Apply date filters
        if alert.after_date:
            queryset = queryset.filter(departure_datetime__gte=alert.after_date)

        if alert.before_date:
            queryset = queryset.filter(departure_datetime__lte=alert.before_date)

        return queryset.order_by("departure_datetime")

    @classmethod
    def get_similar_alerts(cls, ride: Ride):
        """
        Find alerts that match a newly created ride
        """
        alerts = RideAlert.objects.filter(
            departure_town__iexact=ride.departure_town,
            arrival_town__iexact=ride.arrival_town,
            is_active=True,
        )

        # Filter by date if alerts have date constraints
        matched_alerts = []
        for alert in alerts:
            if alert.after_date and ride.departure_datetime < alert.after_date:
                continue
            if alert.before_date and ride.departure_datetime > alert.before_date:
                continue
            matched_alerts.append(alert)

        return matched_alerts

    @classmethod
    def _check_alert_matches(cls, alert: RideAlert):
        """
        Check if alert matches any existing rides and notify user
        """
        if not alert.is_active:
            return

        matching_rides = cls.find_matching_rides(alert)

        # if matching_rides.exists():
        #     # Trigger notification to user
        #     from carpool.tasks import send_alert_matches_notification

        #     transaction.on_commit(
        #         lambda: send_alert_matches_notification.delay(
        #             alert.id, list(matching_rides.values_list("id", flat=True))
        #         )
        #     )

    @classmethod
    def cleanup_old_alerts(cls, days: int = 30):
        """
        Delete or deactivate alerts older than specified days
        """
        cutoff_date = timezone.now() - timedelta(days=days)

        # Either soft delete (deactivate)
        old_alerts = RideAlert.objects.filter(
            created_at__lt=cutoff_date, is_active=True
        )
        count = old_alerts.update(is_active=False)

        return count

    @classmethod
    def notify_users_for_new_ride(cls, ride_id: uuid.UUID):
        """
        Notify users whose alerts match a newly created ride
        """
        try:
            ride = Ride.objects.get(id=ride_id)
        except Ride.DoesNotExist:
            raise ValueError("Ride not found")

        matching_alerts = cls.get_similar_alerts(ride)

        # for alert in matching_alerts:
        #     from carpool.tasks import send_new_ride_notification

        #     transaction.on_commit(
        #         lambda a=alert: send_new_ride_notification.delay(a.id, ride_id)
        #     )

        return len(matching_alerts)
