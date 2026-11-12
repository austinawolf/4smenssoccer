"""Settings for the local proof of concept."""
from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
_render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
_debug_value = os.environ.get("DJANGO_DEBUG")
DEBUG = (_debug_value.lower() in {"1", "true", "yes", "on"}) if _debug_value is not None else not bool(os.environ.get("RENDER"))
SECRET_KEY = os.environ.get("SECRET_KEY", "local-poc-only-change-before-deployment")
if not DEBUG and SECRET_KEY == "local-poc-only-change-before-deployment":
    raise ImproperlyConfigured("Set a unique SECRET_KEY environment variable when DJANGO_DEBUG is false.")

_allowed_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
if _allowed_hosts:
    ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts.split(",") if host.strip()]
elif DEBUG:
    # Local POC accepts development host headers on a home network.
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [host for host in [_render_hostname, "localhost", "127.0.0.1"] if host]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if _render_hostname:
    _render_origin = f"https://{_render_hostname}"
    if _render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_render_origin)

# Render terminates TLS at its proxy and forwards the original scheme.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "siteapp",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ],
    },
}]
WSGI_APPLICATION = "config.wsgi.application"

# SQLite keeps the first local POC self-contained. Move to PostgreSQL when the
# data-backed application work starts.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(os.environ.get("DJANGO_SQLITE_PATH", BASE_DIR / "db.sqlite3")),
    }
}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Los_Angeles"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "staff_login"
LOGIN_REDIRECT_URL = "staff_home"
