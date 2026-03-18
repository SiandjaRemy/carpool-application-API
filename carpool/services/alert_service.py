import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from carpool.models import RideAlert, Ride
from carpool.enums.enums import RideStatus


class RideAlertService:
    """Service layer for ride alert business logic"""

    @staticmethod
    def _validate_alert_dates(alert_data) -> None:
        """Validate that dates are logical"""
        # Only validate if both dates are provided
        if alert_data.get("before_date") and alert_data.get("after_date"):
            if alert_data["before_date"] <= alert_data["after_date"]:
                raise ValueError("Before date must be after after date")
        else:
            raise ValueError("Both dates are required for alert creation")

        # Validate future dates if provided
        if (
            alert_data.get("before_date")
            and alert_data["before_date"] <= timezone.now()
        ):
            raise ValueError("Before date must be in the future")

        if alert_data.get("after_date") and alert_data["after_date"] <= timezone.now():
            raise ValueError("After date must be in the future")

    @staticmethod
    def _validate_alert_dates_update(update_data, instance) -> None:
        """Validate that updated dates are logical"""
        # Validate if both dates are provided
        if update_data.get("before_date") and update_data.get("after_date"):
            if update_data["before_date"] <= update_data["after_date"]:
                raise ValueError("Before date must be after after date")
        elif update_data.get("before_date") and not update_data.get("after_date"):
            if update_data["before_date"] <= instance.after_date:
                raise ValueError("Before date must be after after date")
        elif update_data.get("after_date") and not update_data.get("before_date"):
            if update_data["after_date"] <= timezone.now():
                raise ValueError("After date must be in the future")
            if instance.before_date <= update_data["after_date"]:
                raise ValueError("Before date must be after after date")

    @classmethod
    @transaction.atomic
    def create_alert(cls, user, alert_data):
        """
        Create a new ride alert for a user
        """
        # Validate dates
        cls._validate_alert_dates(alert_data)

        # Check for duplicate active alerts
        existing_alert = RideAlert.objects.filter(
            user=user,
            departure_town__iexact=alert_data["departure_town"],
            arrival_town__iexact=alert_data["arrival_town"],
            is_active=True,
        ).first()

        if existing_alert:
            raise ValueError(
                f"You already have an active alert for {alert_data['departure_town']} → {alert_data['arrival_town']}"
            )

        alert_data["user"] = user
        # Create alert
        alert = RideAlert.objects.create(**alert_data)

        # Immediately check for matching rides
        cls._check_alert_matches(alert)

        return alert

    @classmethod
    @transaction.atomic
    def update_alert(cls, update_data, instance, user):
        """
        Update an existing alert request
        """
        # Might replace this with a query using selectfor update depending on performance
        if instance.user != user:
            raise ValueError("Alert not found or you don't have permission")

        # Validate dates if they're being updated
        # This about mor complex scenarios, one date only is updated
        if update_data.get("before_date") or update_data.get("after_date"):
            cls._validate_alert_dates_update(update_data, instance)

        # Update fields
        for field, value in update_data.items():
            setattr(instance, field, value)

        instance.save(update_fields=list(update_data.keys()) + ["updated_at"])

        return instance

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
            # Add dates to the filter
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
