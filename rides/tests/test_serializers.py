from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from rides.serializers import RideModelSerializer

from datetime import timedelta, datetime
from django.utils import timezone

User = get_user_model()

class RideSerializersTest(APITestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='serializertest@example.com',
            username='serializertestuser',
            password='testpassword',
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.refresh.access_token}')
        
        self.departure_datetime = timezone.now() + timedelta(days=4)

    def test_ride_creation(self):
        data = {
            'departure_town': 'Town A',
            'arrival_town': 'Town B',
            'departure_datetime': self.departure_datetime,
            'available_seats': 2,
            'price_per_seat': 2000,
        }
        context = {
            "user": self.user
        }
        serializer = RideModelSerializer(data=data, context=context)
        self.assertTrue(serializer.is_valid())
        ride = serializer.save()
        self.assertEqual(ride.departure_town, data['departure_town'])
        
        
    def test_missing_required_fileds(self):
        """You can comment any 1 or multiple fileds int the data object to test the serializer"""
        data = {
            # 'departure_town': 'Town A',
            'arrival_town': 'Town B',
            'departure_datetime': self.departure_datetime,
            'available_seats': 2,
            'price_per_seat': 2000,
        }
        context = {
            "user": self.user
        }
        serializer = RideModelSerializer(data=data, context=context)
        
        self.assertFalse(serializer.is_valid())

        self.assertIn("departure_town", serializer.errors)
        # Check the error detail
        self.assertEqual(serializer.errors["departure_town"][0], "This field is required.")


        
        
