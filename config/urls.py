from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.contrib.auth.views import LogoutView

from siteapp.views import section
from siteapp.staff_views import (
    StaffLoginView,
    admin_dashboard,
    cancel_score_submission,
    coach_dashboard,
    decide_score_review,
    photo_dashboard,
    staff_home,
    submit_reconciliation,
    submit_score,
    update_player_photo,
)

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("staff/login/", StaffLoginView.as_view(), name="staff_login"),
    path("staff/logout/", LogoutView.as_view(next_page="staff_login"), name="staff_logout"),
    path("staff/", staff_home, name="staff_home"),
    path("staff/coach/", coach_dashboard, name="staff_coach"),
    path("staff/matches/<int:match_id>/report/", submit_score, name="staff_submit_score"),
    path("staff/matches/<int:match_id>/cancel-report/", cancel_score_submission, name="staff_cancel_score"),
    path("staff/matches/<int:match_id>/reconcile/", submit_reconciliation, name="staff_reconcile_score"),
    path("staff/admin/", admin_dashboard, name="staff_admin"),
    path("staff/photos/", photo_dashboard, name="staff_photos"),
    path("staff/reviews/<int:review_id>/decision/", decide_score_review, name="staff_review_decision"),
    path("staff/players/<int:player_id>/photo/", update_player_photo, name="staff_player_photo"),
    path("", section, {"slug": "home"}, name="home"),
    path("<slug:slug>/", section, name="section"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
