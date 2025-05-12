"""
URL configuration for clothinglibrary project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('allauth.socialaccount.urls')),
    path('catalog/', views.catalog_view, name='catalog'),
    path('catalog/<item_id>/', views.item_detail, name='item_detail'),
    path('add-item/', views.add_item, name='add_item'),
    path('item/<int:pk>/delete', views.ItemDeleteView.as_view(), name='delete_item'),
    path('profile/<str:username>', views.profile, name='profile'),
    path('profile/update_description/', views.update_description, name='update_description'),
    path('profile/update_picture/', views.update_profile_picture, name='update_profile_picture'),
    path('profile/remove_picture/', views.remove_profile_picture, name='remove_profile_picture'),
    path('promote-patrons/', views.PromotePatronsFormView.as_view(), name='promote_patrons'),
    path('item/<item_id>/review/', views.add_review, name='add_review'),
    path('review/<review_id>/delete/', views.delete_review, name='delete_review'),
    path('collection/edit/<int:pk>/', views.CollectionUpdateView.as_view(), name='edit_collection'),
    path('collection/create/', views.CollectionCreateView.as_view(), name='create_collection'),
    path('collection/<int:pk>/delete/', views.CollectionDeleteView.as_view(), name='delete_collection'),
    path('item/<int:item_id>/request_borrow/', views.request_borrow, name='request_borrow'),
    path('my-borrowed-items/', views.my_borrowed_items, name='my_borrowed_items'),
    path('collection/<int:collection_id>/', views.collection_detail, name='collection_detail'),
    path('request_access/<int:collection_id>/', views.request_access, name='request_access'),
    path('manage_requests/', views.manage_requests, name='manage_requests'),
    path('request_librarian/', views.request_librarian, name='request_librarian'),
    path('lender_items/', views.lender_items, name='lender_items'),
    path('item/<int:pk>/delete', views.ItemDeleteView.as_view(), name='delete_item'),
    path('items/<int:item_id>/edit/', views.edit_item, name='edit_item'),
    path('collections/', views.collections_view, name='collections'),
    path('notifications/mark_read/', views.mark_notifications_read, name='mark_notifications_read'),
]
