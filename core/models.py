from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    ROLE_CHOICES = (
        ('user', 'Kullanıcı'),
        ('admin', 'Admin'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        # Yeni kullanıcı oluşturulduğunda profil ve role default 'user' olarak atanır
        Profile.objects.create(user=instance, role='user')
    else:
        # Güncelleme durumunda profile varsa güncelle, yoksa oluştur
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            Profile.objects.create(user=instance, role='user')


# Site ayarları
class SiteSetting(models.Model):
    whatsapp_support_link = models.URLField(verbose_name="WhatsApp Destek Bağlantısı", max_length=300)

    def __str__(self):
        return "Site Ayarları"

    class Meta:
        verbose_name = "Site Ayarı"
        verbose_name_plural = "Site Ayarları"


# Kripto cüzdanları
class CryptoWallet(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    network = models.CharField(max_length=100)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.network}"


# Yatırım paketleri
class Package(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField(verbose_name="Süre (gün)")
    profit_percent = models.PositiveIntegerField(default=100, verbose_name="Getiri Oranı (%)")

    def __str__(self):
        return self.name
    



# Yatırımlar
class Investment(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REFUNDED = 'refunded'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Beklemede'),
        (STATUS_APPROVED, 'Onaylandı'),
        (STATUS_CANCELLED, 'İptal Edildi'),
        (STATUS_REFUNDED, 'İade Edildi'),
    ]

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='investments')
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    expected_return = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Beklenen Getiri")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Yatırım'
        verbose_name_plural = 'Yatırımlar'

    def save(self, *args, **kwargs):
        if not self.expected_return and self.amount and self.package:
            self.expected_return = self.amount * (Decimal(1) + Decimal(self.package.profit_percent) / Decimal(100))

        now = timezone.now()
        if self.status == self.STATUS_APPROVED and not self.approved_at:
            self.approved_at = now
            self.cancelled_at = None
            self.refunded_at = None
        elif self.status == self.STATUS_CANCELLED and not self.cancelled_at:
            self.cancelled_at = now
            self.approved_at = None
            self.refunded_at = None
        elif self.status == self.STATUS_REFUNDED and not self.refunded_at:
            self.refunded_at = now
            self.approved_at = None
            self.cancelled_at = None
        elif self.status == self.STATUS_PENDING:
            self.approved_at = None
            self.cancelled_at = None
            self.refunded_at = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.profile.user.username} - {self.package.name} | {self.amount}₺ | {self.status} | {self.created_at.strftime('%d/%m/%Y')}"


# Yatırım Özeti
class UserInvestmentSummary(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='investment_summary')
    total_invested = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_return = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    pending_payments = models.PositiveIntegerField(default=0)
    has_active_investment = models.BooleanField(default=False)

    def __str__(self):
        return f"Yatırım Özeti - {self.profile.user.username}"

    class Meta:
        verbose_name = "Yatırım Özeti"
        verbose_name_plural = "Yatırım Özetleri"


# Ödeme Onayı
class PaymentConfirmation(models.Model):
    investment = models.OneToOneField(Investment, on_delete=models.CASCADE, related_name='payment_confirmation')
    whatsapp_number = models.CharField(max_length=20)
    payment_screenshot = models.ImageField(upload_to='payment_screenshots/')
    sent_at = models.DateTimeField(auto_now_add=True)
    admin_approved = models.BooleanField(default=False)
    admin_approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.investment.profile.user.username} - Ödeme Onayı ({self.sent_at.strftime('%d/%m/%Y')})"
