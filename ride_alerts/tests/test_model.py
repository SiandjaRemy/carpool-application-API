from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from ride_alerts.models import RideAlert


User = get_user_model()

from django.utils import timezone
from datetime import datetime, timedelta


class RideAlertModelTest(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='modeltest@example.com',
            username='modeltestuser',
            password='testpassword',
        )
        
        self.departure_datetime = timezone.now() + timedelta(days=4)

        self.test_ride_alert = RideAlert.objects.create(
            user=self.user,
            departure_town="Town A",
            arrival_town="Town B",
            departure_datetime=self.departure_datetime,
            available_seats=3,
        )

    def test_create_ride_alert(self):
        ride_alert = RideAlert.objects.create(
            user=self.user,
            departure_town="Town A",
            arrival_town="Town B",
            departure_datetime=self.departure_datetime,
            available_seats=3,
        )
        
        self.assertEqual(ride_alert.user.username, "modeltestuser")
        self.assertEqual(len(RideAlert.objects.all()), 2)
        
                
    def test_create_ride_alert_with_invalid_number_of_seats(self):        
        ride_alert = RideAlert(
            user=self.user,
            departure_town="Town A",
            arrival_town="Town B",
            departure_datetime=self.departure_datetime,
            available_seats=0,
        )

        with self.assertRaises(ValidationError) as context:
            ride_alert.full_clean()
            
        self.assertIn("Ensure this value is greater than or equal to 1.", str(context.exception))

        
    def test_update_ride_alert(self):
        self.test_ride_alert.arrival_town = "Town C"
        self.test_ride_alert.available_seats = 5
        self.test_ride_alert.save()
        
        self.assertEqual(self.test_ride_alert.arrival_town, "Town C")
        self.assertEqual(self.test_ride_alert.available_seats, 5)
    
    
    def test_delete_ride_alert(self):
        self.test_ride_alert.delete()
        
        self.assertEqual(len(RideAlert.objects.all()), 0)
    
    