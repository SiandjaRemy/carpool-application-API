from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from ride_requests.models import RideRequest


User = get_user_model()

from django.utils import timezone
from datetime import datetime, timedelta


class RideRequestModelTest(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='modeltest@example.com',
            username='modeltestuser',
            password='testpassword',
        )
        
        self.departure_datetime = timezone.now() + timedelta(days=4)
        
        self.test_ride_request = RideRequest.objects.create(
            user=self.user,
            departure_town="Town A",
            arrival_town="Town B",
            departure_datetime=self.departure_datetime,
            required_seats=3,
            price_per_seat=1000,
        )

    def test_create_ride_request(self):
        ride_request = RideRequest.objects.create(
            user=self.user,
            departure_town="Town A",
            arrival_town="Town B",
            departure_datetime=self.departure_datetime,
            required_seats=3,
            price_per_seat=1000,
        )
        
        self.assertEqual(ride_request.user.username, "modeltestuser")
        self.assertEqual(ride_request.departure_town, "Town A")
        self.assertEqual(ride_request.required_seats, 3)
        self.assertEqual(len(RideRequest.objects.all()), 2)
        
                
    def test_create_ride_request_with_invalid_number_of_seats(self):        
        ride_request = RideRequest(
            user=self.user,
            departure_town="Town A",
            arrival_town="Town B",
            departure_datetime=self.departure_datetime,
            required_seats=0,
            price_per_seat=1000,
        )

        with self.assertRaises(ValidationError) as context:
            ride_request.full_clean()
            
        self.assertIn("Ensure this value is greater than or equal to 1.", str(context.exception))

        
    def test_update_ride_request(self):
        self.test_ride_request.arrival_town = "Town C"
        self.test_ride_request.price_per_seat = 700
        self.test_ride_request.save()
        
        self.assertEqual(self.test_ride_request.arrival_town, "Town C")
        self.assertEqual(self.test_ride_request.price_per_seat, 700)
    
    
    def test_delete_ride_request(self):
        self.test_ride_request.delete()
        
        self.assertEqual(len(RideRequest.objects.all()), 0)
    
