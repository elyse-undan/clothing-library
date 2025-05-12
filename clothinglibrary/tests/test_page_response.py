from django.test import TestCase, Client

class PageResponseTests(TestCase):
    #landing page
    def test_landing_page_loads(self):
        response = self.client.get("/") 
        self.assertEqual(response.status_code, 200)
    
    #catalog page
    def test_catalog_page_loads(self):
        response = self.client.get("/catalog/") 
        self.assertEqual(response.status_code, 200)

    #collections page
    def test_collections_page_loads(self):
        response = self.client.get("/collections/") 
        self.assertEqual(response.status_code, 200)

    #page doesn't exist
    def test_page_does_not_exist(self):
        response = self.client.get("/nonexistent/")
        self.assertEqual(response.status_code, 404)