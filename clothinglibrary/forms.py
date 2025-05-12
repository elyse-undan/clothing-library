from django.forms import CheckboxSelectMultiple, ModelForm, Form, ModelMultipleChoiceField, Textarea
from clothinglibrary.models import Item, UserProfile
from django.contrib.auth.models import User, Group


class ItemForm(ModelForm):
    class Meta:
        model = Item
        fields = [
            'name', 'description', 'size', 'measurements', 'care_instructions',
            'condition', 'flaws', 'max_rental_duration', 'protection_info', 'category'
        ]
        error_messages = {
            'name': {
                'required': "The item name is required.",
                'max_length': "The name is too long.",
            },
            'description': {
                'required': "Please provide a description for the item.",
            },
            'size': {
                'required': "Please specify the size.",
            },
            'measurements': {
                'required': "Please provide the measurements.",
            },
            'care_instructions': {
                'required': "Please provide care instructions.",
            },
            'condition': {
                'required': "Please select a condition.",
            },
            'max_rental_duration': {
                'required': "Please specify the maximum rental duration (in days).",
            },
            'protection_info': {
                'required': "Please provide protection or insurance details.",
            },
            'category': {
                'required': "Please select a category.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, CheckboxSelectMultiple):
                field.widget.attrs.update({'class': 'form-control'})
        # make max_rental_duration greater than 0
        self.fields['max_rental_duration'].widget.attrs.update({'min': '1'})

class UserProfileForm(ModelForm):
    class Meta:
        model = UserProfile
        fields = ['description', 'photo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, Textarea):
                field.widget.attrs.update({'class': 'form-control'})
            elif field.widget.input_type != 'file':
                field.widget.attrs.update({'class': 'form-control'})

class PromotePatronForm(Form):
    users_to_promote = ModelMultipleChoiceField(
        queryset=User.objects.exclude(groups__name='Librarians').exclude(is_superuser=True),
        widget=CheckboxSelectMultiple,
        label="Select users to promote to Librarian:",
    )

    def promote_users(self):
        for user in self.cleaned_data['users_to_promote']:
            user.groups.add(Group.objects.get(name='Librarians'))
            user.save()