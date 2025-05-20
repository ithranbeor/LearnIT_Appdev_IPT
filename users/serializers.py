from rest_framework import serializers
from .models import *
from .models import Profile


class VideoUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ['title', 'description', 'video_file', 'category']

class CommentSerializer(serializers.ModelSerializer):
    user_profile_picture = serializers.SerializerMethodField()
    user_username = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'content', 'created_at', 'user_profile_picture', 'user_username']  # Add any other necessary fields

    def get_user_profile_picture(self, obj):
        return obj.user.profile.picture.url if obj.user.profile.picture else None

    def get_user_username(self, obj):
        return obj.user.username
    
    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError('Content cannot be empty.')
        return value

class VideoSerializer(serializers.ModelSerializer):
    uploader_username = serializers.CharField(source='uploader.username', read_only=True)
    uploader_profile_picture = serializers.ImageField(source='uploader.profile.picture', read_only=True)

    class Meta:
        model = Video
        fields = '__all__'
        extra_fields = ['uploader_username', 'uploader_profile_picture']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True) 

    class Meta:
        model = Profile
        fields = ['id', 'user', 'picture', 'description']

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['user', 'description', 'picture']  

    def validate_user(self, value):
        if 'username' in value:
            value.pop('username', None)
        return value

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords must match.")
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user