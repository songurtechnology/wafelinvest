from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-vgz7(815#_eb#&0xh2b=j^r+yb)pl)^!qcmjga8jp@rvyq(@^x'

DEBUG = False  # Prod ortamda False yapmayı unutma!

ALLOWED_HOSTS = ['wafelinvest.nl', 'www.wafelinvest.nl']

INSTALLED_APPS = [
    'whitenoise.runserver_nostatic',  # Geliştirme statik servisi için
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'widget_tweaks',  # Form alanları için
    'channels',
    'core',  # Projenin ana app'i
]

ASGI_APPLICATION = 'wafelinvest.asgi.application'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get("redis-cli --tls -u redis://default:AZhKAAIjcDFhMWVkZDc1YmJkYzk0ZjkyOWYxYzUzNGFmOTUwODdlYnAxMA@desired-jackal-38986.upstash.io:6379")],
        },
    },
}



MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Statik dosyalar için
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # Dil ayarları için ekledim
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'wafelinvest.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Proje genel templates klasörü
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # login form için önemli
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wafelinvest.wsgi.application'


DATABASES = {
    'default': dj_database_url.config(
        default='postgresql://wafelinvestdb_t5d7_user:LbbGHIiBe5EiqBdyGVMrveuwYXtpL31p@dpg-d21e3k7fte5s73fggtgg-a.oregon-postgres.render.com/wafelinvestdb_t5d7',
        conn_max_age=600,
        ssl_require=True
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},  # minimum 8 karakter
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Dil ve saat dilimi ayarları
LANGUAGE_CODE = 'tr'  # Türkçe arayüz için
TIME_ZONE = 'Europe/Amsterdam'  # Amsterdam zaman dilimi

USE_I18N = True
USE_L10N = True
USE_TZ = True

# Statik dosyalar
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Medya dosyaları (kullanıcı yüklemeleri)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Güvenlik ayarları (prod ortamda aktif olmalı)
SESSION_COOKIE_SECURE = False  # Prod'da True yap
CSRF_COOKIE_SECURE = False     # Prod'da True yap

# Login ve redirect ayarları
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'packages'  # Giriş sonrası yönlendirilecek URL

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
