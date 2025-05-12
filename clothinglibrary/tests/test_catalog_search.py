from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from clothinglibrary.models import Item, Rental
from datetime import timedelta
from django.utils import timezone


class CatalogSearchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")

        self.available_item = Item.objects.create(
            lender=self.user,
            name="Red Dress",
            size="S",
            condition="NW",
            max_rental_duration=7,
            category="formal"
        )

        self.unavailable_item = Item.objects.create(
            lender=self.user,
            name="Blue Jacket",
            size="M",
            condition="EC",
            max_rental_duration=5,
            category="outerwear"
        )

        self.unavailable_item.rentals.create(
            renter=self.user,
            start_date=timezone.now().date() - timedelta(days=1),
            end_date=timezone.now().date() + timedelta(days=5),
            status='approved'
        )

    def test_search_returns_matching_items(self):
        response = self.client.get(reverse('catalog') + "?q=red")
        self.assertContains(response, "Red Dress")
        self.assertNotContains(response, "Blue Jacket")

    def test_search_returns_nothing_for_invalid_keyword(self):
        response = self.client.get(reverse('catalog') + "?q=nonexistent")
        self.assertNotContains(response, "Red Dress")
        self.assertNotContains(response, "Blue Jacket")
