# forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Profile
from django.contrib.auth.forms import UserCreationForm
from .models import Video
from .models import Comment 
from django.db import models

class EditProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    email = forms.EmailField(required=True)

    class Meta:
        model = Profile
        fields = ['description', 'picture']  # Don't include username and email here

    def __init__(self, *args, **kwargs):
        # Pass user information to the form via initial data
        user = kwargs.pop('user', None)
        super(EditProfileForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['username'].initial = user.username
            self.fields['email'].initial = user.email

    def save(self, commit=True):
        # Save the profile data first
        profile = super(EditProfileForm, self).save(commit=False)
        user = profile.user  # Link to the user model
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']

        # If commit is True, save the user and profile
        if commit:
            user.save()
            profile.save()

        return profile

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_active = False  # Prevent login until email is verified
        if commit:
            user.save()
        return user


class VideoUploadForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['title', 'description', 'video_file', 'category']

        
class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['title', 'description', 'video_file']

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']

CATEGORY_CHOICES = [
    ('Programming & Software Development', 'Programming & Software Development'),
    ('Networking & Cybersecurity', 'Networking & Cybersecurity'),
    ('Artificial Intelligence & Machine Learning', 'Artificial Intelligence & Machine Learning'),
    ('Data Science & Databases', 'Data Science & Databases'),
    ('Cloud Computing & DevOps', 'Cloud Computing & DevOps'),
    ('IT Fundamentals & Certifications', 'IT Fundamentals & Certifications'),
    ('UI/UX Design & Tools', 'UI/UX Design & Tools'),
    ('Game Development & AR/VR', 'Game Development & AR/VR'),
    ('Career & Soft Skills for IT', 'Career & Soft Skills for IT'),
]