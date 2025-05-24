from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.cache import cache
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test, login_required
from django.contrib.auth.signals import user_logged_out
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.forms import PasswordResetForm
from django.views.decorators.cache import never_cache
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.utils.timezone import now
from django.utils import timezone
from django.core.mail import send_mail
from datetime import timedelta
from django.dispatch import receiver
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden

from users.models import SignInActivity

from axes.handlers.proxy import AxesProxyHandler

from .forms import SignUpForm, EditProfileForm, VideoUploadForm, VideoForm

from .models import Video, Category, Profile, Comment, Reply, SignInActivity

from .serializers import ProfileSerializer, ProfileUpdateSerializer, SignupSerializer, VideoSerializer, CommentSerializer, VideoUploadSerializer

from rest_framework import generics, status, permissions, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied

import numpy as np


def video_search(request): 
    search_query = request.GET.get('search', '')
    category = request.GET.get('category', '')

    videos = Video.objects.all()
    if category:
        videos = videos.filter(category=category)

    if search_query:
        # Only keyword matches
        videos = videos.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    else:
        # No search query, show all or recent videos
        videos = videos.order_by('-upload_date')

    context = {
        'videos': videos,
        'search_query': search_query,
        'category': category,
    }
    return render(request, 'users/home.html', context)

def unlock_user(request, user_id):
    if request.method == "POST":
        user = get_object_or_404(User, id=user_id)
        profile = user.profile
        profile.is_locked = False
        profile.save()
        messages.success(request, f"{user.username}'s account has been unlocked.")
    return redirect('admin_dashboard')

def rate_limited_password_reset(request):
    ip = get_client_ip(request)
    key = f'password_reset_attempts_{ip}'
    attempts = cache.get(key, 0)

    if attempts >= 5:
        messages.error(request, "Too many reset attempts. Please try again later.")
        return render(request, 'password_reset_form.html')

    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(request=request)
            cache.set(key, attempts + 1, timeout=3600) 
            return redirect('password_reset_done')
    else:
        form = PasswordResetForm()

    return render(request, 'password_reset_form.html', {'form': form})

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def terms(request):
    return render(request, 'terms.html')

class UserUploadedVideosAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        videos = Video.objects.filter(uploader=user)
        serializer = VideoSerializer(videos, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data
        data['uploader'] = request.user.id 

        serializer = VideoUploadSerializer(data=data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Video uploaded successfully', 'video': serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@login_required
@user_passes_test(lambda u: u.is_superuser) 
def delete_signin_activity(request, activity_id):
    activity = get_object_or_404(SignInActivity, id=activity_id)
    activity.delete()
    return redirect('admin_dashboard')

def search_signin_history(request):
    user_id = request.GET.get('user_id', '')
    username = request.GET.get('username', '')
    month = request.GET.get('month', '')
    year = request.GET.get('year', '')
   
    activities = SignInActivity.objects.all()

    if user_id:
        activities = activities.filter(user__id=user_id)
    if username:
        activities = activities.filter(user__username__icontains=username)
    if month:
        try:
            month = int(month) 
            activities = activities.filter(sign_in_time__month=month)
        except ValueError:
            pass
    if year:
        try:
            year = int(year)  
            activities = activities.filter(sign_in_time__year=year)
        except ValueError:
            pass  

    now = timezone.now()
    last_24_hours = now - timedelta(hours=24)
    recent_activities = SignInActivity.objects.filter(sign_in_time__gte=last_24_hours)

    users = User.objects.all()

    context = {
        'all_activities': activities,
        'recent_activities': recent_activities,
        'users': users,
        'user_id': user_id,
        'username': username,
        'month': month,
        'year': year,
    }

    return render(request, 'admin_dashboard.html', context)

@user_passes_test(lambda u: u.is_superuser)
def delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if not user.is_superuser:
            user.delete()
            messages.success(request, 'User and all associated videos deleted.')
    return redirect('admin_dashboard')

@user_passes_test(lambda u: u.is_superuser)
def delete_video(request, video_id):
    if request.method == 'POST':
        video = get_object_or_404(Video, id=video_id)
        video.delete()
        messages.success(request, 'Video deleted successfully.')
    return redirect('admin_dashboard')

class CommentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, comment_id):
        try:
            comment = Comment.objects.get(id=comment_id)
            if comment.user != request.user:
                return Response({"detail": "You do not have permission to delete this comment."}, status=status.HTTP_403_FORBIDDEN)

            comment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Comment.DoesNotExist:
            return Response({"detail": "Comment not found."}, status=status.HTTP_404_NOT_FOUND)

class VideoCommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        video_id = self.kwargs['video_id']
        return Comment.objects.filter(video_id=video_id)

    def perform_create(self, serializer):
        video = Video.objects.get(id=self.kwargs['video_id'])
        serializer.save(user=self.request.user, video=video)

class VideoCommentDetailView(generics.DestroyAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        if obj.user != self.request.user:
            raise PermissionDenied("You cannot delete other users' comments.")
        return obj

class CommentViewSet(viewsets.ViewSet):
    def list(self, request, video_id=None):
        comments = Comment.objects.filter(video_id=video_id)
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

class DeleteOwnVideoView(generics.DestroyAPIView):
    queryset = Video.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        try:
            video = self.get_object()

            if video.uploader != request.user:
                return Response({'detail': 'You do not have permission to delete this video.'}, status=status.HTTP_403_FORBIDDEN)

            video.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Video.DoesNotExist:
            return Response({'detail': 'Video not found.'}, status=status.HTTP_404_NOT_FOUND)

class UserUploadedVideosAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        videos = Video.objects.filter(uploader=user)
        serializer = VideoSerializer(videos, many=True)
        return Response(serializer.data)

@api_view(['POST'])
def increment_view(request, video_id):
    try:
        video = Video.objects.get(id=video_id)
        video.views += 1
        video.save()
        return Response({'message': 'View incremented successfully.'})
    except Video.DoesNotExist:
        return Response({'error': 'Video not found'}, status=404)

class SignupView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            return Response({
                "access_token": access_token,
                "refresh_token": refresh_token
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        profile = request.user.profile
        
        data = request.data.copy()
        data.pop('user.username', None) 

        serializer = ProfileUpdateSerializer(profile, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Profile updated successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VideoList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        videos = Video.objects.all()
        serializer = VideoSerializer(videos, many=True)
        return Response(serializer.data)

class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated] 

    def get(self, request, *args, **kwargs):
        profile = Profile.objects.get(user=request.user) 
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

class LogoutTimeView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        sign_out_time = request.data.get('logout_time')
        
        if sign_out_time:
            user_activity = SignInActivity.objects.filter(user=request.user, sign_out_time=None).first()

            if user_activity:
                user_activity.sign_out_time = sign_out_time
                user_activity.save()
                return Response({'status': 'Logout time updated'})
            else:
                user_activity = SignInActivity(user=request.user, sign_out_time=sign_out_time)
                user_activity.save()
                return Response({'status': 'Logout time recorded'})

        return Response({'error': 'Invalid data'}, status=400)

class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(request=request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            SignInActivity.objects.create(user=user, sign_in_time=now()) 

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            return Response({
                'message': 'Login successful',
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('login')

@receiver(user_logged_out)
def update_signout_activity(sender, user, request, **kwargs):
    latest_activity = SignInActivity.objects.filter(user=user, sign_out_time__isnull=True).last()
    if latest_activity:
        latest_activity.sign_out_time = now()
        latest_activity.save()

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('choose_account_type')
        else:
            return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Check if the user is locked
        if AxesProxyHandler.is_locked(request, credentials={'username': username}):
            return render(request, 'users/login.html', {
                'error': 'Your account is locked due to too many failed login attempts. Please try again later.'
            })

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)

            # Record login time
            SignInActivity.objects.create(user=user, sign_in_time=now())

            if user.is_superuser:
                return redirect('choose_account_type')
            else:
                return redirect('home')
        else:
            return render(request, 'users/login.html', {'error': 'Invalid credentials'})

    return render(request, 'users/login.html')

def choose_account_type(request):
    if request.method == 'GET':
        account_type = request.GET.get('account_type')

        if account_type == 'regular':
            # Redirect to the regular user home page
            return redirect('home')
        elif account_type == 'admin':
            # Redirect to the admin dashboard
            return redirect('admin_dashboard')
    
    return render(request, 'users/choose_account_type.html')

@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    search_query = request.GET.get('search', '').strip()

    if search_query:
        users = User.objects.filter(
            Q(username__icontains=search_query) |
            Q(id__icontains=search_query)
        ).select_related('profile').prefetch_related('video_set')
    else:
        users = User.objects.all().select_related('profile').prefetch_related('video_set')

    videos = Video.objects.all()

    all_activities = SignInActivity.objects.select_related('user').order_by('-sign_in_time')

    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    recent_activities = all_activities.filter(sign_in_time__gte=twenty_four_hours_ago)

    return render(request, 'admin_dashboard.html', {
        'users': users,
        'videos': videos,
        'all_activities': all_activities,
        'recent_activities': recent_activities,
        'search_query': search_query, 
    })

def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()

        # Optional: ensure profile is created if not already (can be skipped if signal already handles it)
        Profile.objects.get_or_create(user=user)

        # ✅ Specify the backend explicitly to fix the ValueError
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        return redirect('home')
    else:
        return render(request, 'users/activation_invalid.html')
    
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()

            current_site = get_current_site(request)
            subject = 'Activate your LearnIT account'
            message = render_to_string('users/activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            send_mail(subject, message, 'noreply@learnit.com', [user.email])

            return render(request, 'users/verification_sent.html')
    else:
        form = SignUpForm()
    return render(request, 'users/signup.html', {'form': form})

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

@never_cache
@login_required
def home_view(request):
    videos = Video.objects.all().order_by('-upload_date')
    categories = Category.objects.all()  
    search_query = request.GET.get('search', '')
    selected_category = request.GET.get('category', '')

    videos = Video.objects.all()

    if search_query:
        videos = videos.filter(title__icontains=search_query)

    if selected_category:
        videos = videos.filter(category=selected_category)

    context = {
        'videos': videos,
        'CATEGORY_CHOICES': CATEGORY_CHOICES,
    }
    return render(request, 'users/home.html', context)


@never_cache
@login_required
def profile_view(request):
    user = request.user
    user_videos = Video.objects.filter(uploader=user) 
    return render(request, 'users/profile.html', {'user': user, 'user_videos': user_videos})


@login_required
def edit_profile(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = EditProfileForm(instance=profile)

    return render(request, 'users/edit_profile.html', {'form': form})

def upload_video(request):
    if request.method == 'POST' and request.FILES['video_file']:
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.uploader = request.user 
            video.save()
            return redirect('profile')  
    else:
        form = VideoUploadForm()

    return render(request, 'users/upload_video.html', {'form': form})

def video_list(request):
    videos = Video.objects.all().order_by('-upload_date')
    return render(request, 'users/video_list.html', {'videos': videos})


def increment_views(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    video.increment_views() 
    return JsonResponse({"views": video.views})


# Edit Video
def edit_video(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES, instance=video)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = VideoForm(instance=video)
    return render(request, 'users/edit_video.html', {'form': form})

def delete_video(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    if request.method == 'POST':
        video.delete()
        return redirect('profile') 
    return render(request, 'delete_video.html', {'video': video})

def add_comment(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        comment = Comment.objects.create(
            video=video,
            user=request.user,
            content=content
        )
        return redirect('profile')
    
def home_add_comment(request, video_id):
    videos = get_object_or_404(Video, id=video_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        comment = Comment.objects.create(
            video=videos,
            user=request.user,
            content=content
        )
        return redirect('home')
    
def home_delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    if request.user != comment.user:
        return HttpResponseForbidden("You do not have permission to delete this comment.")
    
    video_id = comment.video.id
    comment.delete()
    return redirect('home')    

def add_reply(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        reply = Reply.objects.create(
            comment=comment,
            user=request.user,
            content=content
        )
        return redirect('profile', video_id=comment.video.id)
    
def video_detail(request, video_id):
    video = Video.objects.get(id=video_id)  # Assuming a Video model exists
    return render(request, 'users/video_detail.html', {'video': video})    

def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    if request.user != comment.user:
        return HttpResponseForbidden("You do not have permission to edit this comment.")

    if request.method == 'POST':
        comment.content = request.POST['content']
        comment.save()
        return redirect('video_detail', video_id=comment.video.id)

    return render(request, 'edit_comment.html', {'comment': comment})

# Delete comment view
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    if request.user != comment.user:
        return HttpResponseForbidden("You do not have permission to delete this comment.")
    
    video_id = comment.video.id
    comment.delete()
    return redirect('profile')

def get_video_comments(request, video_id):
    comments = Comment.objects.filter(video_id=video_id)
    comment_data = [
        {
            "user": comment.user.username,
            "content": comment.content,
            "created_at": comment.created_at.strftime("%b %d, %Y, %I:%M %p"),
        }
        for comment in comments
    ]
    return JsonResponse({"comments": comment_data})

def search_videos(request):
    query = request.GET.get('query', '')
    if query:
        # Filter videos based on title, description, or uploader username
        videos = Video.objects.filter(
            title__icontains=query
        ) | Video.objects.filter(
            description__icontains=query
        ) | Video.objects.filter(
            uploader__username__icontains=query
        )

        video_data = [
            {
                'title': video.title,
                'description': video.description,
                'video_file': video.video_file.url,
                'uploader': {
                    'username': video.uploader.username,
                    'profile_picture': video.uploader.profile.picture.url if video.uploader.profile.picture else '/static/image/default_profile.png'
                },
                'upload_date': video.upload_date.strftime('%B %d, %Y'),
                'views': video.views
            }
            for video in videos
        ]
        return JsonResponse({'videos': video_data})
    else:
        return JsonResponse({'videos': []})


