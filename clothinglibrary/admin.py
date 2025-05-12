from django.contrib import admin
from .models import UserProfile, Item, Review, Collection
admin.site.register(UserProfile)
admin.site.register(Item)
admin.site.register(Review)
admin.site.register(Collection)