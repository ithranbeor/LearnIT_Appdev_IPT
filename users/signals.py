from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile
from .utils import embed_text

def generate_embedding(instance):
    combined_text = f"{instance.title} {instance.description}"
    instance.embedding = embed_text(combined_text)
    instance.save()

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()
