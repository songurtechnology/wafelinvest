from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # Kullanıcı işlemleri
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Yatırım paketleri
    path('packages/', views.packages, name='packages'),
    path('packages/<int:package_id>/', views.package_detail, name='package_detail'),
    path('invest/<int:package_id>/', views.invest, name='invest'),

    # Ödeme işlemleri
    path('payment/submit/<int:investment_id>/', views.submit_payment, name='submit_payment'),
    path('payment-success/', views.payment_success, name='payment_success'),


    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms, name='terms'),


    # Profil
    path('profile/', views.profile, name='profile'),
]
