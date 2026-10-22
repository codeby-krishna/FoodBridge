from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from .models import Food, NGOProfile, FoodRequest, Pickup


class FoodBridgeTests(TestCase):

    def setUp(self):
        self.donor = User.objects.create_user(
            username='test_donor',
            password='testpass123'
        )

        self.ngo_user = User.objects.create_user(
            username='test_ngo',
            password='testpass123'
        )

        self.volunteer = User.objects.create_user(
            username='test_volunteer',
            password='testpass123'
        )

        self.ngo = NGOProfile.objects.create(
            user=self.ngo_user,
            organization_name='Test NGO',
            contact='9876543210',
            location='Delhi'
        )

        self.food = Food.objects.create(
            food_name='Test Food',
            quantity='10 plates',
            description='Fresh food for testing',
            location='Delhi',
            contact='9876543210',
            best_before=timezone.now() + timedelta(hours=12),
            donor=self.donor
        )

    def test_food_creation(self):
        self.assertEqual(self.food.food_name, 'Test Food')
        self.assertEqual(self.food.donor, self.donor)

    def test_food_urgency_level(self):
        self.assertEqual(self.food.urgency_level, 'Urgent')

    def test_ngo_profile_creation(self):
        self.assertEqual(self.ngo.organization_name, 'Test NGO')

    def test_food_request_creation(self):
        food_request = FoodRequest.objects.create(
            food=self.food,
            user=self.ngo_user,
            ngo=self.ngo,
            status='Pending'
        )

        self.assertEqual(food_request.status, 'Pending')
        self.assertEqual(food_request.food, self.food)

    def test_pickup_creation(self):
        food_request = FoodRequest.objects.create(
            food=self.food,
            user=self.ngo_user,
            ngo=self.ngo,
            status='Accepted'
        )

        pickup = Pickup.objects.create(
            food_request=food_request,
            volunteer=self.volunteer,
            status='Assigned',
            verification_otp='123456'
        )

        self.assertEqual(pickup.status, 'Assigned')
        self.assertEqual(pickup.verification_otp, '123456')