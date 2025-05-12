from django import forms
from django.utils import timezone
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from clothinglibrary import settings
from .forms import ItemForm, PromotePatronForm, UserProfileForm
from .models import BorrowRequest, Item, PromotionRequest, Rental, UserProfile, ItemPhoto, Review, Collection, CollectionAccessRequest, Notification
import boto3
import uuid
from django.db.models import Q
from django.http import HttpResponse
from django.views.decorators.http import require_POST



def home(request):
    return render(request, 'clothinglibrary/homepage.html')

def catalog(request):
    CATEGORY_ORDER = [
        ('formal', 'Formal Wear'),
        ('casual', 'Casual Wear'),
        ('sports', 'Sportswear'),
        ('vintage', 'Vintage'),
        ('street', 'Streetwear'),
        ('active', 'Activewear'),
        ('denim', 'Denim'),
        ('outerwear', 'Outerwear'),
        ('accessories', 'Accessories'),
        ('other', 'Other'),
    ]
    
    # Build a dictionary keyed by category code, each value is a list of items
    items_by_category = {}
    for code, label in CATEGORY_ORDER:
        items_by_category[code] = Item.objects.filter(category=code).order_by('created_at')

    return render(request, 'clothinglibrary/catalog.html', {
        'CATEGORY_ORDER': CATEGORY_ORDER,
        'items_by_category': items_by_category
    })


def catalog_view(request):
    today = timezone.now().date()
    overdue_rentals = Rental.objects.filter(status='on_loan', end_date__lt=today)
    for rental in overdue_rentals:
        rental.status = 'returned'
        rental.save()

    query = request.GET.get('q', '') #gets the search info from users
    
    # Get available items: we use the is_available property on Item 
    all_items = Item.objects.prefetch_related('photos').all()
    
    if not request.user.is_authenticated or request.user.is_librarian:
        visible_items = []
        for item in all_items:
            item_collections = item.collections.all()
            if not item_collections.exists(): #belongs to no collections
                visible_items.append(item)
            else:
                if all(collection.is_public for collection in item_collections): #if all collections it belongs to are public
                    visible_items.append(item) 
        all_items = visible_items
        
    #if the user searches something
    if query:
        all_items = [item for item in all_items if (
            query.lower() in (item.name or '').lower() or
            query.lower() in (item.description or '').lower() or
            query.lower() in (item.category or '').lower()
    )]

    #available_items = [item for item in all_items if item.is_available]
    
    # Group available items by category using their display names
    category_order = [
        "Formal Wear", "Casual Wear", "Sportswear", "Vintage", "Streetwear",
        "Activewear", "Denim", "Outerwear", "Accessories", "Other"
    ]
    items_by_category = {"All": all_items.copy()}  # <-- Add "All" tab first
    for cat in category_order:
        items_by_category[cat] = []

    for item in all_items:
        cat = item.get_category_display()
        if cat in items_by_category:
            items_by_category[cat].append(item)
        else:
            items_by_category["Other"].append(item)


#for displaying the count of the search
    num_results = len(all_items)
    
    return render(request, 'clothinglibrary/catalog.html', {
        "items_by_category": items_by_category,
        "user": request.user,
        "query": query, 
        "num_results": num_results, 
    })


def collections_view(request):
    query = request.GET.get('q', '')

    all_collections = Collection.objects.all()

    if request.user.is_authenticated:
        access_requests = CollectionAccessRequest.objects.filter(user=request.user, status='APPROVED')
        approved_collections = access_requests.values_list('collection_id', flat=True)

        collections_with_access = []
        for collection in all_collections:
            is_approved = request.user.is_librarian() or collection.id in approved_collections
            if collection.is_public or is_approved:
                collection.is_approved = is_approved
                collection.has_pending_request = CollectionAccessRequest.objects.filter(
                    collection=collection, user=request.user, status='PENDING'
                ).exists()
            collections_with_access.append(collection)
                
    else:
        collections_with_access = [c for c in all_collections if c.is_public]

    #if the user searches something
    if query:
        query_lower = query.lower()
        filtered_collections = []
        for collection in collections_with_access:
            if (query_lower in (collection.title or '').lower() or
                query_lower in (collection.description or '').lower()):
                filtered_collections.append(collection)
                continue
            
            #search items by name in each collection
            if any(query_lower in (item.name or '').lower() for item in collection.items.all()):
                filtered_collections.append(collection)
        
        collections_with_access = filtered_collections

    num_results = len(collections_with_access)

    return render(request, 'clothinglibrary/collections.html', {
        "collections": collections_with_access,
        "user": request.user,
        "query": query,
        "num_results": num_results,
    })

@method_decorator(login_required, name='dispatch')
class CollectionCreateView(CreateView):
    model = Collection
    fields = ['title', 'description', 'items', 'is_public']
    template_name = 'clothinglibrary/create_collection.html'
    success_url = '/collections/'

    def form_valid(self, form):
        if (not form.cleaned_data.get('is_public')) and (not self.request.user.is_librarian()):
            form.add_error('is_public', "You must be a librarian to create a private collection.")
            return self.form_invalid(form)
        items = form.cleaned_data.get('items')
        if items:
            for item in items:
                if Collection.objects.filter(items__in=[item], is_public=False).exists():
                    form.add_error('items', f"{item} is already in a private collection.")
                    return self.form_invalid(form)
        form.instance.creator = self.request.user
        return super().form_valid(form)

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        for field in form:
            if field.name != 'csrf_token':
                widget = field.field.widget
                if not isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                    widget.attrs.update({'class': 'form-control custom-form-control'})
        return form

class CollectionUpdateView(UpdateView):
    model = Collection
    fields = ['title', 'description', 'items']
    template_name = 'clothinglibrary/edit_collection.html'
    success_url = '/collections/'

    def form_valid(self, form):
        items = form.cleaned_data.get('items')
        if items:
            for item in items:
                if Collection.objects.filter(items__in=[item], is_public=False).exists() and item not in form.instance.items.all():
                    form.add_error('items', f"{item} is already in a private collection, so it cannot be added to another collection.")
                    return self.form_invalid(form)
        return super().form_valid(form)

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        for field in form:
            if field.name != 'csrf_token':
                field.field.widget.attrs.update({'class': 'form-control custom-form-control'})
        return form

@method_decorator(login_required, name='dispatch')
class CollectionDeleteView(DeleteView):
    model = Collection
    template_name = 'clothinglibrary/delete_collection.html'
    success_url = '/catalog/'

    # get which collections the user can delete
    def get_queryset(self):
        if self.request.user.is_librarian():
            return Collection.objects.all()
        return self.model.objects.filter(creator=self.request.user)

def profile(request, username):
    user = get_object_or_404(User, username=username)
    return render(request, 'clothinglibrary/profile.html', {'user': user, 'is_current_user': request.user.is_authenticated and
                                                            username == request.user.username, 'uname': request.user.username if request.user.is_authenticated else ""})

@login_required
def add_item(request):
    if not request.user.is_librarian():
        return redirect('home')

    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.lender = request.user
            item.save()
            if 'photo' in request.FILES:
                photo_file = request.FILES['photo']
                # Generate a unique file key for the image
                file_key = f"item_photos/{item.pk}_{uuid.uuid4().hex}_{photo_file.name}"
                # Create an S3 client using credentials from settings
                s3_client = boto3.client('s3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                )
                # Upload the file-like object directly
                s3_client.upload_fileobj(
                    photo_file,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    file_key,
                    ExtraArgs={
                        "CacheControl": "max-age=2628000", # 30 days
                        "ContentType": photo_file.content_type, 
                    },
                )
                # Construct the photo URL
                photo_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{file_key}"
                # Save the ItemPhoto object
                ItemPhoto.objects.create(item=item, photo=photo_url, is_primary=True)

            return redirect('item_detail', item_id=item.pk)
    else:
        form = ItemForm()

    return render(request, 'clothinglibrary/add_item.html', {'form': form})

# Source: ChatGPT
# Prompt: How can I add an edit item feature so that I can return to the page where I created the item and edit features
# Date: April 20, 2025
@login_required
def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)

    # Handles if a user isn't a lender
    if not request.user.is_librarian():
        return redirect('catalog')

    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item) #the form for the current item
        if form.is_valid():
            form.save()

            # Handles how a new photo gets added to the amazon s3 bucket
            if 'photo' in request.FILES:
                photo_file = request.FILES['photo']
                file_key = f"item_photos/{item.pk}_{uuid.uuid4().hex}_{photo_file.name}"

                s3_client = boto3.client('s3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                )

                s3_client.upload_fileobj(
                    photo_file,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    file_key,
                    ExtraArgs={
                        "CacheControl": "max-age=2628000",
                        "ContentType": photo_file.content_type,
                    },
                )

                photo_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{file_key}"

                # Delete existing photo
                item.photos.filter(is_primary=True).delete()

                ItemPhoto.objects.create(item=item, photo=photo_url, is_primary=True)

            return redirect('catalog')
    else:
        form = ItemForm(instance=item)

    return render(request, 'clothinglibrary/edit_item.html', {'form': form, 'item': item})

class ItemDeleteView(DeleteView):
    model = Item
    template_name = 'clothinglibrary/delete_item.html'
    success_url = '/catalog/'
    def get_queryset(self):
        if self.request.user.is_librarian():
            return Item.objects.all()
        # non-librarians can't delete
        return Item.objects.none()

def item_detail(request, item_id):
    item = get_object_or_404(Item.objects.prefetch_related('photos'), pk=item_id)
    borrow_request = None
    if request.user.is_authenticated:
        borrow_request = BorrowRequest.objects.filter(item=item, user=request.user).order_by('-date_requested').first()
    return render(request, 'clothinglibrary/item_detail.html', {'item': item, 'borrow_request': borrow_request})

@login_required
def update_description(request):
    if request.method == 'POST':
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        description = request.POST.get('description', '').strip()
        user_profile.description = description
        user_profile.save()
        messages.success(request, "Description updated successfully.")
    else:
        messages.error(request, "Invalid request method.")
    return redirect('profile', username=request.user.username)

@login_required
def update_profile_picture(request):
    if request.method == 'POST':
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        if 'photo' in request.FILES:
            user_profile.photo = request.FILES['photo']
            user_profile.save()
            messages.success(request, "Profile picture updated successfully.")
        else:
            messages.error(request, "No photo uploaded.")
    else:
        messages.error(request, "Invalid request method.")
    return redirect('profile', username=request.user.username)

@login_required
def remove_profile_picture(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    user_profile.photo = None
    user_profile.save()
    messages.success(request, "Profile picture removed.")
    return redirect('profile', username=request.user.username)

@login_required
def add_review(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    if request.method == 'POST':
        comment = request.POST.get('comment')
        rating = request.POST.get('rating')
        if not comment or not rating:
            messages.error(request, "Comment and rating are required.")

        else: 
            Review.objects.create(
                item=item,
                user=request.user,
                comment=comment,
                rating=rating
            )
            messages.success(request, "Review added successfully.")
            return redirect('item_detail', item_id=item_id)
    return redirect('item_detail', item_id=item_id)

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id)
    if review.user == request.user:  # Ensure the logged-in user is the author
        messages.success(request, "Review deleted successfully.")
        review.delete()
    return redirect('item_detail', item_id=review.item.id)

@method_decorator(login_required, name='dispatch')
# TODO: make this redirect to 404 instead of infinite redirect loop
@method_decorator(user_passes_test(lambda u: u.is_librarian()), name='dispatch')
class PromotePatronsFormView(FormView):
    template_name = 'clothinglibrary/promote_patrons.html'
    form_class = PromotePatronForm
    success_url = reverse_lazy('home')
    def form_valid(self, form):
        if not self.request.user.is_librarian():
            form.add_error(None, 'You must be a librarian to promote other users.')
        if form.errors:
            return self.form_invalid(form)
        form.promote_users()
        messages.success(self.request, "Selected users have been promoted to librarians.")
        return super().form_valid(form)


@login_required
def request_borrow(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    if not item.is_available:
        return redirect('item_detail', item_id=item_id)

    if request.user.is_librarian and item.lender == request.user:
        messages.error(request, "You cannot borrow your own item.")
        return redirect('item_detail', item_id=item_id)
    
    if BorrowRequest.objects.filter(item=item, user=request.user, status='PENDING').exists():
        return redirect('item_detail', item_id=item_id)

    if request.method == 'POST':
        duration_input = request.POST.get('desired_duration', '7')
        try:
            patron_duration = int(duration_input)
        except ValueError:
            patron_duration = 7

        BorrowRequest.objects.create(
            item=item,
            user=request.user,
            desired_duration=patron_duration,
            status='PENDING'
        )

    return redirect('item_detail', item_id=item_id)

@login_required
def my_borrowed_items(request):
    current_rentals = Rental.objects.filter(renter=request.user, status='on_loan')
    borrow_requests = BorrowRequest.objects.filter(user=request.user, status='PENDING').order_by('-date_requested')

    return render(request, 'clothinglibrary/my_borrowed_items.html', {'borrow_requests': borrow_requests, 'current_rentals': current_rentals})

@user_passes_test(lambda u: u.is_librarian())
def manage_requests(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        request_type = request.POST.get('request_type')
        request_id = request.POST.get('request_id')

        if request_type == 'borrow':
            borrow_request = get_object_or_404(BorrowRequest, pk=request_id)

            if action == 'approve':
                borrow_request.status = 'APPROVED'
                borrow_request.date_approved = timezone.now()
                borrow_request.due_date = timezone.now().date() + timezone.timedelta(days=borrow_request.desired_duration)
                borrow_request.save()

                try:
                    # Create rental with status "on_loan" to mark the item as borrowed
                    Rental.objects.create(
                        item=borrow_request.item,
                        renter=borrow_request.user,
                        start_date=timezone.now().date(),
                        end_date=borrow_request.due_date,
                        status='on_loan'
                    )
                    messages.success(request, f"Borrow request for {borrow_request.item.name} approved.")
                except Exception as e:
                    error_message = f"Error approving the borrow request: {e}"
                    messages.error(request, error_message)
                    borrow_request.status = 'PENDING'
                    borrow_request.save()
                    return redirect('manage_requests')

            elif action == 'deny':
                borrow_request.status = 'DENIED'
                borrow_request.save()
                messages.error(request, f"Borrow request for {borrow_request.item.name} denied.")

        elif request_type == 'access':
            access_request = get_object_or_404(CollectionAccessRequest, pk=request_id)

            if action == 'approve':
                access_request.status = 'APPROVED'
                access_request.date_approved = timezone.now()
                access_request.save()
                messages.success(request, f"Access request for {access_request.collection.title} approved.")

            elif action == 'deny':
                access_request.status = 'DENIED'
                access_request.save()
                messages.error(request, f"Access request for {access_request.collection.title} denied.")

        elif request_type == 'promotion':
            promo_request = get_object_or_404(PromotionRequest, pk=request_id)

            if action == 'approve':
                promo_request.status = 'APPROVED'
                promo_request.save()
            # Here we elevate the user to a librarian. Implementation depends on your app’s logic.
                user_to_promote = promo_request.user
                user_to_promote.is_librarian = True
                user_to_promote.save()
                messages.success(request, f"{user_to_promote.username} has been promoted to librarian.")
        
            elif action == 'deny':
                promo_request.status = 'DENIED'
                promo_request.save()
                messages.error(request, f"Promotion request for {promo_request.user.username} denied.")

        return redirect('manage_requests')

    pending_borrow_requests = BorrowRequest.objects.filter(status='PENDING').select_related('item', 'user')
    pending_access_requests = CollectionAccessRequest.objects.filter(status='PENDING').select_related('collection', 'user')
    pending_promotion_requests = PromotionRequest.objects.filter(status='PENDING').select_related('user')

    return render(request, 'clothinglibrary/manage_requests.html', {'pending_borrow_requests': pending_borrow_requests, 'pending_access_requests': pending_access_requests, 'pending_promotion_requests': pending_promotion_requests})

def collection_detail(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id)

    if not collection.is_public:
        if request.user.is_librarian:
            items_in_collection = collection.items.all()
        else:
            access_request = CollectionAccessRequest.objects.filter(collection=collection, user=request.user).first()
            if not access_request or access_request.status != 'APPROVED':
                return redirect('request_access', collection_id=collection.id)
    else:
        items_in_collection = collection.items.all()

    query = request.GET.get('q', '')

    #if the user searches something
    if query:
        query_lower = query.lower()
        items_in_collection = [item for item in items_in_collection if (
            query_lower in (item.name or '').lower() or
            query_lower in (item.description or '').lower() or
            query_lower in (item.category or '').lower()
        )]

    num_results = len(items_in_collection)

    return render(request, 'clothinglibrary/collection_detail.html', {
        'collection': collection,
        'items_in_collection': items_in_collection,
        'query': query,
        'num_results': num_results,
    })

@login_required
def request_access(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id)

    if collection.is_public:
        return redirect('collection_detail', collection_id=collection.id)

    existing_request = CollectionAccessRequest.objects.filter(collection=collection, user=request.user).first()

    if existing_request:
        if existing_request.status == 'PENDING':
            messages.info(request, f"Your request for access to '{collection.title}' is still pending.")
        elif existing_request.status == 'APPROVED':
            messages.success(request, f"Your request for access to '{collection.title}' has been approved.")
        elif existing_request.status == 'DENIED':
            messages.error(request, f"Your request for access to '{collection.title}' was denied. Please contact a librarian if you have any questions.")

    if request.method == 'POST':
        if not existing_request:
            CollectionAccessRequest.objects.create(
                collection=collection,
                user=request.user,
                status='PENDING'
            )
            messages.success(request, f"Request for access to '{collection.title}' submitted successfully. Please wait for approval.")
        elif existing_request.status == 'DENIED':
            existing_request.status = 'PENDING'
            existing_request.save()
            messages.success(request, f"Your request for access to '{collection.title}' is now pending. Please wait for approval.")

    return render(request, 'clothinglibrary/request_access.html', {
        'collection': collection,
        'existing_request': existing_request,
    })

@login_required
def request_librarian(request):
    # Determine the URL to redirect back to – default to home if no referrer found
    redirect_url = request.META.get("HTTP_REFERER", "/")

    # Create a new promotion request if none is pending
    if not PromotionRequest.objects.filter(user=request.user, status='PENDING').exists():
        PromotionRequest.objects.create(user=request.user)
        messages.success(request, "Your promotion request has been submitted.")
    else:
        messages.info(request, "Your promotion request is already pending.")
    
    return redirect(redirect_url)

def lender_items(request):
    all_items = Item.objects.filter(lender=request.user)
    borrowed_items = [item for item in all_items if not item.is_available]
    available_items = [item for item in all_items if item.is_available]
    
    # Pass the borrowed items first, then available ones.
    return render(request, 'clothinglibrary/profile.html', {
        'borrowed_items': borrowed_items,
        'available_items': available_items,
    })

@require_POST
@login_required
def mark_notifications_read(request):
    request.user.notifications.all().delete()
    return HttpResponse("OK")