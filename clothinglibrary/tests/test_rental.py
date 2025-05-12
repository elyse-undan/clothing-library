from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth.models import User
from clothinglibrary.models import Item, Rental
from datetime import timedelta
from django.utils import timezone

class RentalFunctionalityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")
        self.renter = User.objects.create_user(username="renter", password="pass123")

        self.available_item = Item.objects.create(
            lender=self.user,
            name="Green Sweater",
            size="M",
            condition="NW",
            max_rental_duration=7,
            category="casual"
        )

        self.unavailable_item = Item.objects.create(
            lender=self.user,
            name="Red Skirt",
            size="S",
            condition="EC",
            max_rental_duration=5,
            category="formal"
        )

        # Create a rental for the unavailable item
        self.unavailable_item.rentals.create(
            renter=self.renter,
            start_date=timezone.now().date() - timedelta(days=2),
            end_date=timezone.now().date() + timedelta(days=3),
            status='approved'
        )

    def test_item_rental_create(self):
        rental = Rental.objects.create(
            renter=self.renter,
            item=self.available_item,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=3),
            status='approved'
        )
        self.assertEqual(rental.renter, self.renter)
        self.assertEqual(rental.item, self.available_item)
        self.assertEqual(rental.status, 'approved')

    def test_item_availability_after_rental(self):
        rental = Rental.objects.create(
            renter=self.renter,
            item=self.available_item,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=3),
            status='approved'
        )
        self.available_item.refresh_from_db()
        self.assertFalse(self.available_item.is_available)

    def test_item_availability_status(self):
        self.assertTrue(self.available_item.is_available)
        self.assertFalse(self.unavailable_item.is_available)

    def test_rental_duration_limit(self):
        rental = Rental(
            renter=self.user,
            item=self.available_item,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=10),
            status='approved'
        )
        with self.assertRaises(ValidationError):
            rental.clean()