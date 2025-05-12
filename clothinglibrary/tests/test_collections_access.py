from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from clothinglibrary.models import Collection, CollectionAccessRequest

User = get_user_model()

class CollectionAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.patron = User.objects.create_user(username="patron", password="testpass")
        self.librarian = User.objects.create_user(username="librarian", password="testpass", is_staff=True)

        self.public_collection = Collection.objects.create(
            title='Public Collection',
            is_public=True,
            creator=self.patron
        )
        self.private_collection = Collection.objects.create(
            title='Private Collection',
            is_public=False,
            creator=self.patron
        )

        self.dashboard_url = reverse("profile", kwargs={"username": self.user.username})

    def test_logged_in_user(self):
        self.client.login(username="testuser", password="password")
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

    def test_public_collection_accessible_by_patron(self):
        self.client.login(username='patron', password='testpass')
        url = reverse('collection_detail', kwargs={'collection_id': self.public_collection.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_private_collection_accessible_with_approved_access_request(self):
        CollectionAccessRequest.objects.create(
            user=self.patron,
            collection=self.private_collection,
            status='APPROVED'
        )
        self.client.login(username='patron', password='testpass')
        url = reverse('collection_detail', kwargs={'collection_id': self.private_collection.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_private_collection_accessible_by_librarian(self):
        self.client.login(username='librarian', password='testpass')
        url = reverse('collection_detail', kwargs={'collection_id': self.private_collection.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)