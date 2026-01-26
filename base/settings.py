import os
from pathlib import Path

# -------------------------------------------------
# BASE DIRECTORY
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent


# -------------------------------------------------
# SECURITY SETTINGS
# -------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

DEBUG = os.environ.get("DEBUG", "False").lower() in ["true", "1", "yes"]

ALLOWED_HOSTS = ["skiliteent.pythonanywhere.com", "127.0.0.1", "localhost", "172.20.10.9"]


CSRF_TRUSTED_ORIGINS = [
    "https://skiliteent.pythonanywhere.com",
]


# -------------------------------------------------
# SITE URL / PROTOCOL
# -------------------------------------------------
# -------------------------------------------------
# BASE SITE URL (Single Source of Truth)
# -------------------------------------------------
BASE_SITE_URL = os.environ.get("BASE_SITE_URL", "http://127.0.0.1:8000")


# -------------------------------------------------
# APPLICATIONS
# -------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Your apps
    'digital_id',
    'admin_dash',
    'id_card',
    'officers_dash',
    'password_reset',
    'payments',

    # Third-party
    'widget_tweaks',
    'rest_framework',
]


# -------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# -------------------------------------------------
# URL CONFIG
# -------------------------------------------------
ROOT_URLCONF = 'base.urls'


# -------------------------------------------------
# TEMPLATES
# -------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'digital_id.context_processors.notifications',
                'digital_id.context_processors.pending_requests_count',
            ],
        },
    },
]


# -------------------------------------------------
# WSGI
# -------------------------------------------------
WSGI_APPLICATION = 'base.wsgi.application'


# -------------------------------------------------
# DATABASE (SQLite – OK for PythonAnywhere free)
# -------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# -------------------------------------------------
# PASSWORD VALIDATION
# -------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# -------------------------------------------------
# INTERNATIONALIZATION
# -------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# -------------------------------------------------
# STATIC FILES
# -------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'


# -------------------------------------------------
# MEDIA FILES
# -------------------------------------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# -------------------------------------------------
# CUSTOM USER MODEL
# -------------------------------------------------
AUTH_USER_MODEL = 'digital_id.User'


# -------------------------------------------------
# AUTH REDIRECTS
# -------------------------------------------------
LOGIN_URL = "/login/"
LOGOUT_REDIRECT_URL = "/login/"
LOGIN_REDIRECT_URL = "/officer/officer-dash/"


# -------------------------------------------------
# PAYSTACK SETTINGS (FROM ENVIRONMENT)
# -------------------------------------------------
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY")


# -------------------------------------------------
# EMAIL SETTINGS (GMAIL SMTP)
# -------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.environ.get("EMAIL_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_PASSWORD")

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# -------------------------------------------------
# OPTIONAL: SECURITY HARDENING (Production)
# -------------------------------------------------
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
