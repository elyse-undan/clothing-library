from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

class DashboardAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.dashboard_url = reverse("profile", kwargs={"username": self.user.username})

    #user is logged in, is able to access the profile page
    def test_logged_in_user(self):
        self.client.login(username="testuser", password="password") 
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200) 
