from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from datetime import datetime, timedelta, timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils.timezone import now
import json

# Modeller ve formlar...
from .models import (
    Package, Investment, PaymentConfirmation, CryptoWallet, 
    UserInvestmentSummary, Profile, User
)
from .forms import (
    RegisterForm, InvestmentForm, PaymentConfirmationForm, LoginForm
)

RETURN_RATES = {
    20: 0.30,
    50: 0.35,
    100: 0.40,
    150: 0.45,
    200: 0.50,
    250: 0.55,
    300: 0.60,
    350: 0.65,
    400: 0.70,
    450: 0.75,
    500: 0.80,
    550: 0.85,
    600: 0.90,
    650: 0.95,
    700: 1.00,
    800: 1.10,
    1000: 1.20,
    1200: 1.35,
    1500: 1.50,
    2000: 1.50,
}


def calculate_expected_return(package, amount):
    try:
        if (
            package is not None
            and package.profit_percent is not None
            and amount is not None
        ):
            return round(float(amount) * (float(package.profit_percent) / 100), 2)
    except Exception as e:
        print("HATA:", e)
    return None




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
    packages = Package.objects.all()[:3]  # Sadece 3 tanesini al
    return render(request, 'core/home.html', {'packages': packages, 'year': datetime.now().year})


def packages(request):
    packages = Package.objects.all()
    return render(request, 'core/packages.html', {'packages': packages})

def packages_by_category(request, category):
    if category == "basic":
        packages = Package.objects.filter(price__gte=100, price__lt=250)
    elif category == "premium":
        packages = Package.objects.filter(price__gte=250, price__lt=500)
    elif category == "master":
        packages = Package.objects.filter(price__gte=500, price__lte=2000)
    else:
        packages = Package.objects.none()

    return render(request, 'core/packages.html', {
        'packages': packages,
        'category': category.capitalize(),
    })

def package_detail(request, pk):
    package = get_object_or_404(Package, pk=pk)

    expected_return = None
    if package.price and package.profit_percent:
        try:
            expected_return = package.price * (package.profit_percent / 100)
        except Exception:
            expected_return = None

    context = {
        'package': package,
        'expected_return': expected_return,
        'duration': package.duration_days,  # ✳️ Bu satır EKLENSİN
    }
    return render(request, 'core/package_detail.html', context)


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

    expected_return = calculate_expected_return(package, package.price)
    print("PRICE:", package.price)
    print("PROFIT:", package.profit_percent)
    print("EXPECTED RETURN:", expected_return)

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
            print("❌ FORM INVALID")
            print("FORM ERRORS:", form.errors.as_json())
            messages.error(request, 'Formda hata var.')
    else:
        form = InvestmentForm(profile=profile, package=package)

    return render(request, 'core/invest.html', {
        'form': form,
        'package': package,
        'expected_return': expected_return,
        'duration': package.duration_days,
        'description': package.description,
        'profit_percent': package.profit_percent,
    })


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
            return redirect('payment_success', investment_id=investment.id)
        else:
            messages.error(request, 'Geçerli bir dosya yükleyin.')
    else:
        form = PaymentConfirmationForm()

    crypto_wallet = CryptoWallet.objects.filter(active=True).first()
  

    context = {
        'form': form,
        'investment': investment,
        'crypto_wallet': crypto_wallet,
        "support_email": "wafelinvest@gmail.com",
    }
    return render(request, 'core/submit_payment.html', context)

@login_required
def payment_success(request, investment_id):
    investment = get_object_or_404(Investment, id=investment_id)
    context = {
        'investment': investment,
    }
    return render(request, 'core/payment_success.html', context)

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




