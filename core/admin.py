from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.html import format_html
from .models import (
    Package,
    Investment,
    PaymentConfirmation,
    CryptoWallet,
    SiteSetting,
    UserInvestmentSummary,
    Profile
)

# User admin kaydını kaldır
admin.site.unregister(User)

# User admin yeniden kaydediliyor
@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'last_login')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone_number', 'address')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'phone_number')


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('whatsapp_support_link',)

    def has_add_permission(self, request):
        return SiteSetting.objects.count() < 1


@admin.register(CryptoWallet)
class CryptoWalletAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'network', 'active')
    list_filter = ('active', 'network')
    search_fields = ('name', 'address', 'network')
    fields = ('name', 'address', 'network', 'active')


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'profit_percent')
    search_fields = ('name',)
    list_editable = ('price', 'duration_days', 'profit_percent')


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = (
        'get_username', 'package', 'amount', 'expected_return', 'status',
        'created_at', 'approved_at', 'cancelled_at', 'refunded_at'
    )
    list_filter = ('status', 'package')
    search_fields = ('profile__user__username', 'profile__user__email', 'package__name')
    readonly_fields = ('expected_return', 'created_at', 'approved_at', 'cancelled_at', 'refunded_at')

    def get_username(self, obj):
        return getattr(obj.profile.user, 'username', '-') or '-'
    get_username.short_description = 'Kullanıcı'

    def save_model(self, request, obj, form, change):
        if 'status' in form.changed_data:
            now = timezone.now()
            if obj.status == Investment.STATUS_APPROVED:
                obj.approved_at = now
                obj.cancelled_at = None
                obj.refunded_at = None
            elif obj.status == Investment.STATUS_CANCELLED:
                obj.cancelled_at = now
                obj.approved_at = None
                obj.refunded_at = None
            elif obj.status == Investment.STATUS_REFUNDED:
                obj.refunded_at = now
                obj.approved_at = None
                obj.cancelled_at = None
            else:
                obj.approved_at = None
                obj.cancelled_at = None
                obj.refunded_at = None

        super().save_model(request, obj, form, change)

        if hasattr(obj.profile, 'user') and hasattr(obj.profile, 'investment_summary'):
            update_user_investment_summary(obj.profile)


@admin.register(PaymentConfirmation)
class PaymentConfirmationAdmin(admin.ModelAdmin):
    list_display = (
        'investment', 'whatsapp_number', 'admin_approved',
        'admin_approved_at', 'sent_at', 'payment_screenshot_preview'
    )
    list_filter = ('admin_approved',)
    search_fields = ('whatsapp_number', 'investment__profile__user__username', 'investment__profile__user__email')
    readonly_fields = ('sent_at', 'admin_approved_at', 'payment_screenshot_preview')
    fields = (
        'investment',
        'whatsapp_number',
        'payment_screenshot',
        'payment_screenshot_preview',
        'admin_approved',
        'sent_at',
        'admin_approved_at',
    )

    def save_model(self, request, obj, form, change):
        if 'admin_approved' in form.changed_data:
            obj.admin_approved_at = timezone.now() if obj.admin_approved else None
        super().save_model(request, obj, form, change)

        if hasattr(obj.investment.profile, 'investment_summary'):
            update_user_investment_summary(obj.investment.profile)

    def payment_screenshot_preview(self, obj):
        if obj.payment_screenshot:
            return format_html('<img src="{}" width="150" />', obj.payment_screenshot.url)
        return "-"
    payment_screenshot_preview.short_description = "Ödeme Görseli"


@admin.register(UserInvestmentSummary)
class UserInvestmentSummaryAdmin(admin.ModelAdmin):
    list_display = (
        'get_username', 'total_invested', 'total_return',
        'pending_payments', 'has_active_investment'
    )
    search_fields = (
        'profile__user__username', 'profile__user__first_name',
        'profile__user__last_name', 'profile__user__email'
    )
    readonly_fields = ('total_invested', 'total_return', 'pending_payments')
    fields = ('profile', 'total_invested', 'total_return', 'pending_payments', 'has_active_investment')

    def get_username(self, obj):
        return getattr(obj.profile.user, 'username', '-') or '-'
    get_username.short_description = 'Kullanıcı'


# Yardımcı fonksiyon: Özet güncelleme
def update_user_investment_summary(profile):
    summary, _ = UserInvestmentSummary.objects.get_or_create(profile=profile)
    investments = profile.investments.filter(status=Investment.STATUS_APPROVED)

    summary.total_invested = sum(inv.amount for inv in investments)
    summary.total_return = sum(inv.expected_return for inv in investments)
    summary.pending_payments = profile.investments.filter(status=Investment.STATUS_PENDING).count()
    summary.has_active_investment = investments.exists()
    summary.save()
