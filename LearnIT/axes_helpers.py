# axes_helpers.py

from django.contrib.auth import get_user_model

User = get_user_model()

def is_not_superuser(request, username):
    try:
        user = User.objects.get(username=username)
        # If user is superuser, return False to prevent lockout
        return not user.is_superuser
    except User.DoesNotExist:
        # If user not found, apply lockout normally
        return True
