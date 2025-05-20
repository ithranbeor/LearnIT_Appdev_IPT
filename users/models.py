# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now, timedelta
from django.core.exceptions import ValidationError

def validate_video_size(value):
    file_size = value.size
    max_size = 100 * 1024 * 1024
    if file_size > max_size:
        raise ValidationError('File size exceeds the 100MB limit.')

class SignInActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sign_in_time = models.DateTimeField(auto_now_add=True)
    sign_out_time = models.DateTimeField(null=True, blank=True)

    def is_recent(self):
        return now() - self.sign_in_time <= timedelta(hours=24)

    def __str__(self):
        return f"{self.user.username} - {self.sign_in_time} to {self.sign_out_time or 'Still signed in'}"
    
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.jpg')
    is_locked = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

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


class Video(models.Model):
    uploader = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    video_file = models.FileField(upload_to='videos/')
    upload_date = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    views = models.PositiveIntegerField(default=0)
    embedding = models.BinaryField(null=True, blank=True) 

    def __str__(self):
        return self.title
    
    def increment_views(self):
        self.views += 1
        self.save()

class Comment(models.Model):
    video = models.ForeignKey(Video, related_name='comments', on_delete=models.CASCADE)
    text = models.TextField() 
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:50] 

class Reply(models.Model):
    comment = models.ForeignKey(Comment, related_name='replies', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField() 
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:50] 