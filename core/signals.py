from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile
from django.core.exceptions import ObjectDoesNotExist

@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    # Sadece normal kullanıcılar için profile oluştur
    if not instance.is_staff and not instance.is_superuser:
        if created:
            Profile.objects.get_or_create(user=instance)
        else:
            try:
                instance.profile.save()
            except ObjectDoesNotExist:
                Profile.objects.create(user=instance)
