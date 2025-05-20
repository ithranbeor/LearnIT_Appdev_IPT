from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.urls import path
from .views import VideoList
from .views import LoginView
from django.conf import settings
from django.conf.urls.static import static
from .views import ProfileAPIView, ProfileUpdateView, SignupView, UserUploadedVideosAPIView, CommentDeleteView, logout_view, LogoutTimeView, rate_limited_password_reset, video_search

urlpatterns = [
    
    # API Endpoints
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/logout/', LogoutTimeView.as_view(), name='logout'),
    path('api/videos/', VideoList.as_view(), name='video-list'),
    path('api/profile/', ProfileAPIView.as_view(), name='profile-api'),
    path('api/upload_video/', UserUploadedVideosAPIView.as_view(), name='upload_video'),
    path('api/profile/update/', ProfileUpdateView.as_view(), name='profile-update'),
    path('api/signup/', SignupView.as_view(), name='signup'),
    path('api/videos/<int:video_id>/increment_view/', views.increment_view),
    path('api/profile/videos/', UserUploadedVideosAPIView.as_view(), name='user-uploaded-videos'),
    path('api/profile/videos/<int:pk>/', views.DeleteOwnVideoView.as_view(), name='delete_own_video'),
    path('api/comments/<int:video_id>/', views.CommentViewSet.as_view({'get': 'list'})),
    path('api/videos/<int:video_id>/comments/', views.VideoCommentListCreateView.as_view(), name='video-comments'),
    path('api/comments/<int:comment_id>/', views.VideoCommentDetailView.as_view(), name='video-comment-detail'),
    path('api/comments/<int:comment_id>/delete/', CommentDeleteView.as_view(), name='comment_delete'),

    # Web Views
    path('', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('home/', views.home_view, name='home'),
    path('profile/', views.profile_view, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('upload/', views.upload_video, name='upload_video'),
    path('viewVideo/', views.video_list, name='video_list'),
    path('edit_video/<int:video_id>/', views.edit_video, name='edit_video'),
    path('delete_video/<int:video_id>/', views.delete_video, name='delete_video'),
    path('logout/', logout_view, name='logout'),  
    path('video/<int:video_id>/', views.video_detail, name='video_detail'),
    path('comment/<int:video_id>/', views.add_comment, name='add_comment'),
    path('reply/<int:comment_id>/', views.add_reply, name='add_reply'),
    path('add_comment/<int:video_id>/', views.add_comment, name='add_comment'),
    path('home_add_comment/<int:video_id>/', views.home_add_comment, name='home_add_comment'),
    path('home_delete_comment/<int:comment_id>/', views.home_delete_comment, name='home_delete_comment'),
    path('edit_comment/<int:comment_id>/', views.edit_comment, name='edit_comment'),
    path('delete_comment/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    path('comments/<int:video_id>/', views.get_video_comments, name='get_video_comments'),
    path('search_videos/', views.search_videos, name='search_videos'),
    path('video/<int:video_id>/increment_views/', views.increment_views, name='increment_views'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('choose_account_type/', views.choose_account_type, name='choose_account_type'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('delete_user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('delete_video/<int:video_id>/', views.delete_video, name='delete_video'),
    path('search-signin-history/', views.search_signin_history, name='search_signin_history'),
    path('delete-signin/<int:activity_id>/', views.delete_signin_activity, name='delete_signin_activity'),
    path('terms/', views.terms, name='terms'),
    path("accounts/password_reset/", rate_limited_password_reset, name="password_reset"),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    path('unlock_user/<int:user_id>/', views.unlock_user, name='unlock_user'),
    path('videos/search/', video_search, name='video_search'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
