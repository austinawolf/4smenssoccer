from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from siteapp.views import section

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", section, {"slug": "home"}, name="home"),
    path("<slug:slug>/", section, name="section"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
