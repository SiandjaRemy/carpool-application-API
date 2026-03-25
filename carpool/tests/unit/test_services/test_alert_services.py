import pytest
from datetime import timedelta
from django.utils import timezone
from unittest.mock import MagicMock

from carpool.services.alert_service import RideAlertService
from carpool.enums.enums import RideStatus
from carpool.tests.factories import (
    UserFactory,
    RideAlertFactory,
    RideFactory,
)

pytestmark = pytest.mark.unit


class TestRideAlertService:
    """Unit tests for ride alert service"""

    # ----------------------------------------------------------------------
    # Create Alert Tests
    # ----------------------------------------------------------------------

    def test_create_alert_happy_path(self, db):
        """Test creating an alert successfully with valid dates"""
        user = UserFactory()
        now = timezone.now()
        alert_data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "before_date": now + timedelta(days=7),
            "after_date": now + timedelta(days=1),
        }

        alert = RideAlertService.create_alert(user=user, alert_data=alert_data)

        assert alert.id is not None
        assert alert.user == user
        assert alert.departure_town == "New York"
        assert alert.arrival_town == "Boston"
        assert alert.is_active is True
        assert alert.before_date is not None
        assert alert.after_date is not None

    def test_create_alert_missing_both_dates(self, db):
        """Test creating alert without both dates raises error"""
        user = UserFactory()
        alert_data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            # No dates provided
        }

        with pytest.raises(
            ValueError, match="Both dates are required for alert creation"
        ):
            RideAlertService.create_alert(user=user, alert_data=alert_data)

    def test_create_alert_missing_one_date(self, db):
        """Test creating alert with only one date raises error"""
        user = UserFactory()
        now = timezone.now()
        alert_data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "before_date": now + timedelta(days=7),
            # Missing after_date
        }

        with pytest.raises(
            ValueError, match="Both dates are required for alert creation"
        ):
            RideAlertService.create_alert(user=user, alert_data=alert_data)

    def test_create_alert_invalid_date_relationship(self, db):
        """Test creating alert with before_date <= after_date"""
        user = UserFactory()
        now = timezone.now()
        alert_data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "before_date": now + timedelta(days=1),
            "after_date": now + timedelta(days=7),  # Before is earlier than after
        }

        with pytest.raises(ValueError, match="Before date must be after after date"):
            RideAlertService.create_alert(user=user, alert_data=alert_data)

    def test_create_alert_past_before_date(self, db):
        """Test creating alert with before_date in the past"""
        user = UserFactory()
        now = timezone.now()
        alert_data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "before_date": now - timedelta(days=1),  # Past date
            "after_date": now + timedelta(days=7),
        }

        with pytest.raises(ValueError, match="Before date must be "):
            RideAlertService.create_alert(user=user, alert_data=alert_data)

    def test_create_alert_past_after_date(self, db):
        """Test creating alert with after_date in the past"""
        user = UserFactory()
        now = timezone.now()
        alert_data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "before_date": now + timedelta(days=7),
            "after_date": now - timedelta(days=1),  # Past date
        }

        with pytest.raises(ValueError, match="After date must be in the future"):
            RideAlertService.create_alert(user=user, alert_data=alert_data)

    def test_create_duplicate_alert(self, db):
        """Test creating duplicate active alert for same route"""
        user = UserFactory()
        now = timezone.now()
        alert_data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "before_date": now + timedelta(days=7),
            "after_date": now + timedelta(days=1),
        }

        # Create first alert
        RideAlertService.create_alert(user=user, alert_data=alert_data)

        # Try to create duplicate
        with pytest.raises(ValueError, match="already have an active alert"):
            RideAlertService.create_alert(user=user, alert_data=alert_data)

    def test_create_alert_same_route_inactive_allowed(self, db):
        """Test creating alert for same route if previous is inactive"""
        user = UserFactory()
        now = timezone.now()
        alert_data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "before_date": now + timedelta(days=7),
            "after_date": now + timedelta(days=1),
        }

        # Create first alert and deactivate it
        alert1 = RideAlertService.create_alert(user=user, alert_data=alert_data)
        alert1.is_active = False
        alert1.save()

        # Creating another should work
        alert2 = RideAlertService.create_alert(user=user, alert_data=alert_data)
        assert alert2.id != alert1.id
        assert alert2.is_active is True

    # ----------------------------------------------------------------------
    # Update Alert Tests
    # ----------------------------------------------------------------------

    def test_update_alert_happy_path(self, db):
        """Test updating an alert successfully"""
        user = UserFactory()
        now = timezone.now()
        alert = RideAlertFactory(
            user=user,
            departure_town="Old City",
            arrival_town="Old Town",
            before_date=now + timedelta(days=10),
            after_date=now + timedelta(days=5),
        )

        update_data = {
            "departure_town": "New City",
            "before_date": now + timedelta(days=8),
        }

        updated = RideAlertService.update_alert(
            update_data=update_data, instance=alert, user=user
        )

        assert updated.departure_town == "New City"
        assert updated.arrival_town == "Old Town"  # Unchanged
        assert updated.before_date == now + timedelta(days=8)
        assert updated.after_date == now + timedelta(days=5)  # Unchanged

    def test_update_alert_wrong_user(self, db):
        """Test updating another user's alert raises error"""
        user = UserFactory()
        other_user = UserFactory()
        alert = RideAlertFactory(user=other_user)

        update_data = {"departure_town": "New City"}

        with pytest.raises(
            ValueError, match="Alert not found or you don't have permission"
        ):
            RideAlertService.update_alert(
                update_data=update_data, instance=alert, user=user
            )

    def test_update_alert_both_dates_valid(self, db):
        """Test updating both dates with valid relationship"""
        user = UserFactory()
        now = timezone.now()
        alert = RideAlertFactory(
            user=user,
            before_date=now + timedelta(days=10),
            after_date=now + timedelta(days=5),
        )

        update_data = {
            "before_date": now + timedelta(days=8),
            "after_date": now + timedelta(days=3),
        }

        updated = RideAlertService.update_alert(
            update_data=update_data, instance=alert, user=user
        )

        assert updated.before_date == now + timedelta(days=8)
        assert updated.after_date == now + timedelta(days=3)

    def test_update_alert_both_dates_invalid_relationship(self, db):
        """Test updating both dates with before <= after"""
        user = UserFactory()
        now = timezone.now()
        alert = RideAlertFactory(
            user=user,
            before_date=now + timedelta(days=10),
            after_date=now + timedelta(days=5),
        )

        update_data = {
            "before_date": now + timedelta(days=3),
            "after_date": now + timedelta(days=7),  # Before is earlier
        }

        with pytest.raises(ValueError, match="Before date must be after after date"):
            RideAlertService.update_alert(
                update_data=update_data, instance=alert, user=user
            )

    def test_update_alert_only_before_date_valid(self, db):
        """Test updating only before_date with valid relationship to existing after_date"""
        user = UserFactory()
        now = timezone.now()
        alert = RideAlertFactory(
            user=user,
            before_date=now + timedelta(days=10),
            after_date=now + timedelta(days=5),
        )

        # Valid update - new before date after existing after
        update_data = {"before_date": now + timedelta(days=8)}
        updated = RideAlertService.update_alert(
            update_data=update_data, instance=alert, user=user
        )
        assert updated.before_date == now + timedelta(days=8)

        # Invalid update - new before date before existing after
        update_data = {"before_date": now + timedelta(days=4)}
        with pytest.raises(ValueError, match="Before date must be after after date"):
            RideAlertService.update_alert(
                update_data=update_data, instance=alert, user=user
            )

    def test_update_alert_only_after_date_valid(self, db):
        """Test updating only after_date with valid relationship to existing before_date"""
        user = UserFactory()
        now = timezone.now()
        alert = RideAlertFactory(
            user=user,
            before_date=now + timedelta(days=10),
            after_date=now + timedelta(days=5),
        )

        # Valid update - new after date before existing before
        update_data = {"after_date": now + timedelta(days=7)}
        updated = RideAlertService.update_alert(
            update_data=update_data, instance=alert, user=user
        )
        assert updated.after_date == now + timedelta(days=7)

        # Invalid update - new after date after existing before
        update_data = {"after_date": now + timedelta(days=12)}
        with pytest.raises(ValueError, match="Before date must be after after date"):
            RideAlertService.update_alert(
                update_data=update_data, instance=alert, user=user
            )

    def test_update_alert_only_after_date_future_check(self, db):
        """Test updating only after_date checks future date"""
        user = UserFactory()
        now = timezone.now()
        alert = RideAlertFactory(
            user=user,
            before_date=now + timedelta(days=10),
            after_date=now + timedelta(days=5),
        )

        # Past after_date should fail
        update_data = {"after_date": now - timedelta(days=1)}
        with pytest.raises(ValueError, match="After date must be in the future"):
            RideAlertService.update_alert(
                update_data=update_data, instance=alert, user=user
            )

    def test_update_alert_no_date_changes(self, db):
        """Test updating non-date fields without validation"""
        user = UserFactory()
        alert = RideAlertFactory(user=user)

        update_data = {"departure_town": "New City"}

        updated = RideAlertService.update_alert(
            update_data=update_data, instance=alert, user=user
        )

        assert updated.departure_town == "New City"
        assert updated.before_date == alert.before_date  # Dates unchanged

    # ----------------------------------------------------------------------
    # Toggle Alert Tests
    # ----------------------------------------------------------------------

    def test_toggle_alert(self, db):
        """Test toggling alert active status"""
        user = UserFactory()
        alert = RideAlertFactory(user=user, is_active=True)

        toggled = RideAlertService.toggle_alert(alert_id=alert.id, user=user)

        assert toggled.is_active is False

        # Toggle again
        toggled_again = RideAlertService.toggle_alert(alert_id=alert.id, user=user)
        assert toggled_again.is_active is True

    def test_toggle_alert_wrong_user(self, db):
        """Test toggling another user's alert raises error"""
        user = UserFactory()
        other_user = UserFactory()
        alert = RideAlertFactory(user=other_user)

        with pytest.raises(ValueError, match="Alert not found"):
            RideAlertService.toggle_alert(alert_id=alert.id, user=user)

    def test_toggle_nonexistent_alert(self, db):
        """Test toggling alert that doesn't exist"""
        user = UserFactory()

        with pytest.raises(ValueError, match="Alert not found"):
            RideAlertService.toggle_alert(
                alert_id="00000000-0000-0000-0000-000000000000", user=user
            )

    # ----------------------------------------------------------------------
    # Find Matching Rides Tests
    # ----------------------------------------------------------------------

    def test_find_matching_rides(self, db):
        """Test finding rides that match an alert"""
        user = UserFactory()
        now = timezone.now()
        alert = RideAlertFactory(
            user=user,
            departure_town="New York",
            arrival_town="Boston",
            after_date=now + timedelta(days=1),
            before_date=now + timedelta(days=7),
        )

        # Create matching rides
        ride1 = RideFactory(
            departure_town="New York",
            arrival_town="Boston",
            departure_datetime=now + timedelta(days=3),
            status=RideStatus.SCHEDULED,
            available_seats=3,
        )
        ride2 = RideFactory(
            departure_town="New York",
            arrival_town="Boston",
            departure_datetime=now + timedelta(days=5),
            status=RideStatus.SCHEDULED,
            available_seats=2,
        )
        # Create non-matching rides
        RideFactory(
            departure_town="New York",
            arrival_town="Philadelphia",  # Wrong destination
            departure_datetime=now + timedelta(days=4),
        )
        RideFactory(
            departure_town="New York",
            arrival_town="Boston",
            departure_datetime=now + timedelta(days=10),  # Too late
            status=RideStatus.SCHEDULED,
        )
        RideFactory(
            departure_town="New York",
            arrival_town="Boston",
            departure_datetime=now + timedelta(days=0.5),  # Too early
            status=RideStatus.SCHEDULED,
        )
        RideFactory(
            departure_town="New York",
            arrival_town="Boston",
            departure_datetime=now + timedelta(days=4),
            status=RideStatus.CANCELLED,  # Wrong status
        )

        matches = RideAlertService.find_matching_rides(alert)

        assert matches.count() == 2
        assert ride1 in matches
        assert ride2 in matches

    def test_find_matching_rides_no_date_filters(self, db):
        """Test finding rides for alert without date filters"""
        user = UserFactory()
        now = timezone.now()
        alert = RideAlertFactory(
            user=user,
            departure_town="New York",
            arrival_town="Boston",
            after_date=None,
            before_date=None,
        )

        # Create rides
        ride1 = RideFactory(
            departure_town="New York",
            arrival_town="Boston",
            departure_datetime=now + timedelta(days=1),
            status=RideStatus.SCHEDULED,
        )
        ride2 = RideFactory(
            departure_town="New York",
            arrival_town="Boston",
            departure_datetime=now + timedelta(days=10),
            status=RideStatus.SCHEDULED,
        )

        matches = RideAlertService.find_matching_rides(alert)

        assert matches.count() == 2
        assert ride1 in matches
        assert ride2 in matches

    def test_find_matching_rides_case_insensitive(self, db):
        """Test that town matching is case-insensitive"""
        user = UserFactory()
        now = timezone.now()
        alert = RideAlertFactory(
            user=user,
            departure_town="New York",
            arrival_town="Boston",
        )

        ride = RideFactory(
            departure_town="NEW YORK",  # Uppercase
            arrival_town="boston",  # Lowercase
            departure_datetime=now + timedelta(days=3),
            status=RideStatus.SCHEDULED,
        )

        matches = RideAlertService.find_matching_rides(alert)
        assert ride in matches

    # ----------------------------------------------------------------------
    # Get Similar Alerts Tests
    # ----------------------------------------------------------------------

    def test_get_similar_alerts(self, db):
        """Test finding alerts that match a ride"""
        now = timezone.now()
        ride = RideFactory(
            departure_town="New York",
            arrival_town="Boston",
            departure_datetime=now + timedelta(days=3),
        )

        # Create matching alerts
        alert1 = RideAlertFactory(
            departure_town="New York",
            arrival_town="Boston",
            after_date=now + timedelta(days=1),
            before_date=now + timedelta(days=7),
            is_active=True,
        )
        alert2 = RideAlertFactory(
            departure_town="New York",
            arrival_town="Boston",
            after_date=now + timedelta(days=2),
            before_date=now + timedelta(days=5),
            is_active=True,
        )
        # Create non-matching alerts
        RideAlertFactory(  # Wrong route
            departure_town="New York",
            arrival_town="Philadelphia",
            is_active=True,
        )
        RideAlertFactory(  # Inactive
            departure_town="New York",
            arrival_town="Boston",
            is_active=False,
        )
        RideAlertFactory(  # Date too late
            departure_town="New York",
            arrival_town="Boston",
            before_date=now + timedelta(days=2),  # Ride is at day 3, too late
            after_date=now + timedelta(days=1),
            is_active=True,
        )

        matches = RideAlertService.get_similar_alerts(ride)

        assert len(matches) == 2
        assert alert1 in matches
        assert alert2 in matches

    def test_get_similar_alerts_no_date_constraints(self, db):
        """Test finding alerts without date constraints"""
        now = timezone.now()
        ride = RideFactory(
            departure_town="New York",
            arrival_town="Boston",
            departure_datetime=now + timedelta(days=3),
        )

        alert = RideAlertFactory(
            departure_town="New York",
            arrival_town="Boston",
            after_date=None,
            before_date=None,
            is_active=True,
        )

        matches = RideAlertService.get_similar_alerts(ride)
        assert alert in matches
        assert len(matches) == 1

    # ----------------------------------------------------------------------
    # Cleanup Old Alerts Tests
    # ----------------------------------------------------------------------

    def test_cleanup_old_alerts(self, db, freezer):
        """Test deactivating old alerts"""
        now = timezone.now()
        freezer.move_to(now)

        user = UserFactory()

        # Create old alert (40 days ago)
        freezer.move_to(now - timedelta(days=40))
        old_alert = RideAlertFactory(user=user, is_active=True)

        # Create recent alert (10 days ago)
        freezer.move_to(now - timedelta(days=10))
        recent_alert = RideAlertFactory(user=user, is_active=True)

        # Create borderline alert (20 days ago)
        freezer.move_to(now - timedelta(days=20))
        borderline_alert = RideAlertFactory(user=user, is_active=True)

        # Create old alert (31 days ago)
        freezer.move_to(now - timedelta(days=31))
        another_old_alert = RideAlertFactory(user=user, is_active=True)

        # Move back to now
        freezer.move_to(now)

        # Clean up alerts older than 30 days
        count = RideAlertService.cleanup_old_alerts(days=30)

        assert count == 2  # old_alert and borderline_alert

        old_alert.refresh_from_db()
        another_old_alert.refresh_from_db()

        recent_alert.refresh_from_db()
        borderline_alert.refresh_from_db()

        assert old_alert.is_active is False
        assert another_old_alert.is_active is False

        assert borderline_alert.is_active is True
        assert recent_alert.is_active is True

    def test_cleanup_old_alerts_custom_days(self, db, freezer):
        """Test cleanup with custom days parameter"""
        now = timezone.now()
        freezer.move_to(now)

        user = UserFactory()

        # Create alerts of different ages
        freezer.move_to(now - timedelta(days=60))
        very_old = RideAlertFactory(user=user, is_active=True)

        freezer.move_to(now - timedelta(days=15))
        recent = RideAlertFactory(user=user, is_active=True)

        freezer.move_to(now)

        # Clean up alerts older than 20 days
        count = RideAlertService.cleanup_old_alerts(days=20)

        assert count == 1
        very_old.refresh_from_db()
        recent.refresh_from_db()
        assert very_old.is_active is False
        assert recent.is_active is True

    # ----------------------------------------------------------------------
    # Notify Users For New Ride Tests
    # ----------------------------------------------------------------------

    def test_notify_users_for_new_ride(self, db):
        """Test counting alerts that match a new ride"""
        now = timezone.now()
        ride = RideFactory(
            departure_town="New York",
            arrival_town="Boston",
            departure_datetime=now + timedelta(days=3),
        )

        # Create matching alerts
        RideAlertFactory(
            departure_town="New York",
            arrival_town="Boston",
            after_date=now + timedelta(days=1),
            before_date=now + timedelta(days=7),
            is_active=True,
        )
        RideAlertFactory(
            departure_town="New York",
            arrival_town="Boston",
            after_date=now + timedelta(days=2),
            before_date=now + timedelta(days=5),
            is_active=True,
        )
        # Create non-matching
        RideAlertFactory(
            departure_town="New York",
            arrival_town="Boston",
            after_date=now + timedelta(days=5),  # Too late
            before_date=now + timedelta(days=10),
            is_active=True,
        )

        count = RideAlertService.notify_users_for_new_ride(ride.id)

        assert count == 2

    def test_notify_users_for_new_ride_not_found(self, db):
        """Test notifying for non-existent ride"""
        with pytest.raises(ValueError, match="Ride not found"):
            RideAlertService.notify_users_for_new_ride(
                ride_id="00000000-0000-0000-0000-000000000000"
            )

    def test_notify_users_for_new_ride_no_matches(self, db):
        """Test when no alerts match the ride"""
        now = timezone.now()
        ride = RideFactory(
            departure_town="New York",
            arrival_town="Boston",
            departure_datetime=now + timedelta(days=3),
        )

        # Create non-matching alerts
        RideAlertFactory(  # Wrong route
            departure_town="New York",
            arrival_town="Philadelphia",
            is_active=True,
        )
        RideAlertFactory(  # Inactive
            departure_town="New York",
            arrival_town="Boston",
            is_active=False,
        )

        count = RideAlertService.notify_users_for_new_ride(ride.id)
        assert count == 0

    # ----------------------------------------------------------------------
    # Check Alert Matches (Private Method)
    # ----------------------------------------------------------------------

    def test_check_alert_matches_called_on_create(self, db, monkeypatch):
        """Test that _check_alert_matches is called when creating alert"""
        user = UserFactory()
        now = timezone.now()
        alert_data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "before_date": now + timedelta(days=7),
            "after_date": now + timedelta(days=1),
        }

        # Mock the _check_alert_matches method
        mock_check = MagicMock()
        monkeypatch.setattr(RideAlertService, "_check_alert_matches", mock_check)

        alert = RideAlertService.create_alert(user=user, alert_data=alert_data)

        mock_check.assert_called_once_with(alert)

    def test_check_alert_matches_inactive_alert(self, db):
        """Test that _check_alert_matches does nothing for inactive alert"""
        user = UserFactory()
        alert = RideAlertFactory(user=user, is_active=False)

        # This should not raise any errors
        result = RideAlertService._check_alert_matches(alert)
        assert result is None  # Method returns nothing

    # ----------------------------------------------------------------------
    # Edge Cases and Validation Tests
    # ----------------------------------------------------------------------

    def test_create_alert_with_equal_dates(self, db):
        """Test creating alert with before_date equal to after_date"""
        user = UserFactory()
        now = timezone.now()
        alert_data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "before_date": now + timedelta(days=7),
            "after_date": now + timedelta(days=7),  # Equal dates
        }

        with pytest.raises(ValueError, match="Before date must be after after date"):
            RideAlertService.create_alert(user=user, alert_data=alert_data)

    def test_update_alert_with_equal_dates(self, db):
        """Test updating alert with before_date equal to after_date"""
        user = UserFactory()
        now = timezone.now()
        alert = RideAlertFactory(
            user=user,
            before_date=now + timedelta(days=10),
            after_date=now + timedelta(days=5),
        )

        update_data = {
            "before_date": now + timedelta(days=7),
            "after_date": now + timedelta(days=7),  # Equal dates
        }

        with pytest.raises(ValueError, match="Before date must be after after date"):
            RideAlertService.update_alert(
                update_data=update_data, instance=alert, user=user
            )
