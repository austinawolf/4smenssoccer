from django.contrib import admin
from django.urls import path

from siteapp.views import section

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", section, {"slug": "home"}, name="home"),
    path("<slug:slug>/", section, name="section"),
]
