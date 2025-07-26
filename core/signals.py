from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from .models import Profile

@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    # Sadece normal kullanıcılar (admin değil) için profil oluştur
    if instance.is_staff or instance.is_superuser:
        return

    try:
        # Yeni kullanıcı ise profil oluştur
        if created:
            Profile.objects.get_or_create(user=instance)
        else:
            # Var olan kullanıcıda profil varsa kaydet, yoksa oluştur
            if hasattr(instance, 'profile'):
                instance.profile.save()
            else:
                Profile.objects.create(user=instance)
    except Exception as e:
        # Hata loglamak istenirse buraya yazılabilir
        print(f"[Profile Signal] Hata: {e}")
