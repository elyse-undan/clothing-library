from django.test import TestCase
from django.contrib.auth.models import User
from clothinglibrary.models import Item

class ItemCreationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")

    def test_item_creation(self):
        item = Item.objects.create(
            lender=self.user,
            name="Blue T-shirt",
            size="M",
            condition="NW",
            max_rental_duration=7,
            category="casual"
        )
        self.assertEqual(item.name, "Blue T-shirt")
        self.assertEqual(item.size, "M")
        self.assertEqual(item.condition, "NW")
        self.assertEqual(item.max_rental_duration, 7)
        self.assertEqual(item.category, "casual")
        self.assertEqual(item.lender, self.user)
