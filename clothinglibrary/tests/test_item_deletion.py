from django.test import TestCase
from django.contrib.auth.models import User
from clothinglibrary.models import Item

class ItemDeletionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")
        self.item = Item.objects.create(
            lender=self.user,
            name="Red T-shirt",
            size="L",
            condition="NW",
            max_rental_duration=7,
            category="casual"
        )

    def test_item_deletion(self):
        self.item.delete()
        with self.assertRaises(Item.DoesNotExist):
            Item.objects.get(id=self.item.id)
