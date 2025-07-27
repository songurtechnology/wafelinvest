from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils.timezone import now
import json

from .models import (
    Package, Investment, PaymentConfirmation, CryptoWallet,
    SiteSetting, UserInvestmentSummary, Profile
)
from .forms import (
    RegisterForm, InvestmentForm, PaymentConfirmationForm, LoginForm
)

def calculate_expected_return(package, amount):
    profit_percent = Decimal(package.profit_percent or 0)
    return amount * (Decimal(1) + profit_percent / Decimal(100))

def update_user_investment_summary(profile):
    approved_investments = Investment.objects.filter(profile=profile, status=Investment.STATUS_APPROVED)
    aggregates = approved_investments.aggregate(
        total_invested=Sum('amount'),
        total_return=Sum('expected_return')
    )
    total_invested = aggregates['total_invested'] or Decimal('0')
    total_return = aggregates['total_return'] or Decimal('0')

    pending_payments_count = PaymentConfirmation.objects.filter(
        investment__profile=profile,
        admin_approved=False
    ).count()

    summary, _created = UserInvestmentSummary.objects.get_or_create(profile=profile)
    summary.total_invested = total_invested
    summary.total_return = total_return
    summary.pending_payments = pending_payments_count
    summary.has_active_investment = approved_investments.exists()
    summary.save()

def home(request):
    return render(request, 'core/home.html', {'year': datetime.now().year})

def packages(request):
    packages = Package.objects.all()
    return render(request, 'core/packages.html', {'packages': packages})

def package_details(request, pk):
    package = get_object_or_404(Package, pk=pk)
    return_rate = package.profit_percent or 0
    expected_return = package.price * return_rate / 100 if return_rate else 0
    context = {
        'package': package,
        'return_rate': return_rate,
        'expected_return': expected_return,
    }
    return render(request, 'package_details.html', context)


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            auth_login(request, user)
            messages.success(request, 'Kayıt başarılı! Hoş geldiniz.')
            return redirect('profile')
        else:
            messages.error(request, 'Formda hata var, lütfen tekrar kontrol edin.')
    else:
        form = RegisterForm()
    return render(request, 'core/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, 'Giriş başarılı.')
            next_url = request.GET.get('next') or 'profile'
            return redirect(next_url)
        else:
            messages.error(request, 'Kullanıcı adı veya şifre yanlış.')
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'Çıkış yaptınız.')
    return redirect('home')

@login_required
def invest(request, package_id):
    package = get_object_or_404(Package, id=package_id)
    profile = request.user.profile
    if request.method == 'POST':
        form = InvestmentForm(request.POST, profile=profile, package=package)
        if form.is_valid():
            investment = form.save(commit=False)
            investment.profile = profile
            investment.package = package
            investment.expected_return = calculate_expected_return(package, investment.amount)
            investment.status = Investment.STATUS_PENDING
            try:
                investment.clean()
                investment.save()
                messages.success(request, 'Yatırım kaydedildi. Şimdi ödeme dekontunuzu yükleyin.')
                return redirect('submit_payment', investment_id=investment.id)
            except ValidationError as e:
                form.add_error(None, e)
        else:
            messages.error(request, 'Formda hata var.')
    else:
        form = InvestmentForm(profile=profile, package=package)
    return render(request, 'core/invest.html', {'form': form, 'package': package})

@login_required
def submit_payment(request, investment_id):
    profile = request.user.profile
    investment = get_object_or_404(Investment, id=investment_id, profile=profile)

    if PaymentConfirmation.objects.filter(investment=investment).exists():
        messages.info(request, 'Bu yatırım için zaten ödeme dekontu gönderdiniz.')
        return redirect('profile')

    if request.method == 'POST':
        post_data = request.POST.copy()
        post_data['investment'] = str(investment.id)
        form = PaymentConfirmationForm(post_data, request.FILES)
        if form.is_valid():
            confirmation = form.save(commit=False)
            confirmation.investment = investment
            confirmation.save()
            update_user_investment_summary(profile)
            messages.success(request, 'Dekont gönderildi. Onay bekleniyor.')
            return redirect('payment_success')
        else:
            messages.error(request, 'Geçerli bir dosya yükleyin.')
    else:
        form = PaymentConfirmationForm()

    crypto_wallet = CryptoWallet.objects.filter(active=True).first()
    site_setting = SiteSetting.objects.first()
    whatsapp_link = site_setting.whatsapp_support_link if site_setting else "#"

    context = {
        'form': form,
        'investment': investment,
        'crypto_wallet': crypto_wallet,
        'whatsapp_link': whatsapp_link,
    }
    return render(request, 'core/submit_payment.html', context)

@login_required
def payment_success(request):
    return render(request, 'core/payment_success.html')

@login_required
def profile(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('admin:index')

    user = request.user
    profile = user.profile
    summary = UserInvestmentSummary.objects.filter(profile=profile).first()

    approved_investments = Investment.objects.filter(
        profile=profile,
        status=Investment.STATUS_APPROVED
    ).order_by('approved_at')

    countdowns = []
    for inv in approved_investments:
        if inv.approved_at and inv.package and inv.package.duration_days:
            countdown_end = inv.approved_at + timedelta(days=inv.package.duration_days)
            countdowns.append({
                'id': inv.id,
                'package': inv.package.name,
                'amount': float(inv.amount),
                'end_date': countdown_end.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'approved_date': inv.approved_at.strftime("%d.%m.%Y"),
            })

    countdowns_json = json.dumps(countdowns)

    monthly_investments = {}
    for inv in approved_investments:
        key = inv.approved_at.strftime('%Y-%m') if inv.approved_at else inv.created_at.strftime('%Y-%m')
        monthly_investments[key] = monthly_investments.get(key, 0) + float(inv.amount)

    investment_chart_labels = sorted(monthly_investments.keys())
    investment_chart_data = [monthly_investments[label] for label in investment_chart_labels]

    package_distribution = approved_investments.values('package__name').annotate(total=Sum('amount'))

    monthly_returns = {}
    for inv in approved_investments:
        key = inv.approved_at.strftime('%Y-%m') if inv.approved_at else inv.created_at.strftime('%Y-%m')
        monthly_returns[key] = monthly_returns.get(key, 0) + float(inv.expected_return or 0)

    returns_chart_labels = sorted(monthly_returns.keys())
    returns_chart_data = [monthly_returns[label] for label in returns_chart_labels]

    return render(request, 'core/profile.html', {
        'user': user,
        'summary': summary,
        'countdowns': countdowns,
        'countdowns_json': countdowns_json,
        'investment_chart': {
            'labels': investment_chart_labels,
            'data': investment_chart_data,
        },
        'returns_chart': {
            'labels': returns_chart_labels,
            'data': returns_chart_data,
        },
        'package_chart': {
            'labels': [item['package__name'] for item in package_distribution],
            'data': [float(item['total']) for item in package_distribution],
        },
    })

def privacy_policy(request):
    return render(request, 'core/privacy_policy.html')

def terms(request):
    return render(request, 'core/terms.html')
