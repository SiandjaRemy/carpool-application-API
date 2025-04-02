from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from rides_and_requests.models import Ride, RideRequest, RideAlert

User = get_user_model()

from django.utils import timezone
from datetime import datetime, timedelta

class RideModelTest(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='modeltest@example.com',
            username='modeltestuser',
            password='testpassword',
        )

        
        self.test_ride = Ride.objects.create(
            user=self.user,
            departure_town="Town A",
            arrival_town="Town B",
            departure_datetime=timezone.now(),
            available_seats=3,
            price_per_seat=1000,
        )

    def test_create_ride(self):
        ride = Ride.objects.create(
            user=self.user,
            departure_town="Town A",
            arrival_town="Town B",
            departure_datetime=timezone.now(),
            available_seats=3,
            price_per_seat=1000,
        )
        
        self.assertEqual(ride.user.username, "modeltestuser")
        self.assertEqual(len(Ride.objects.all()), 2)
        
        
        
    def test_create_ride_with_invalid_number_of_seats(self):        
        ride = Ride(
            user=self.user,
            departure_town="Town A",
            arrival_town="Town B",
            departure_datetime=timezone.now(),
            available_seats=0,
            price_per_seat=1000,
        )

        with self.assertRaises(ValidationError) as context:
            ride.full_clean()
            
        self.assertIn("Ensure this value is greater than or equal to 1.", str(context.exception))

        
        
    def test_update_ride(self):
        self.test_ride.arrival_town = "Town C"
        self.test_ride.price_per_seat = 700
        self.test_ride.save()
        
        self.assertEqual(self.test_ride.arrival_town, "Town C")
        self.assertEqual(self.test_ride.price_per_seat, 700)
    
    
    def test_delete_ride(self):
        self.test_ride.delete()
        
        self.assertEqual(len(Ride.objects.all()), 0)
    
    