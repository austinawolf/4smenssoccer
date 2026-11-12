from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from django.utils import timezone

from .models import (
    Award,
    CoachAssignment,
    GalleryItem,
    Match,
    MatchAppearance,
    MatchEvent,
    Player,
    PublicContent,
    RosterMembership,
    Season,
    SeasonRules,
    SeasonTeam,
    ScoreReview,
    ScoreSubmission,
    StaffProfile,
    Team,
)


class StaffProfileInline(admin.StackedInline):
    model = StaffProfile
    can_delete = False
    extra = 0


class LeagueUserAdmin(UserAdmin):
    inlines = (StaffProfileInline,)


admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), LeagueUserAdmin)


class SeasonTeamInline(admin.TabularInline):
    model = SeasonTeam
    extra = 1


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "year", "term", "is_active", "is_published")
    list_filter = ("year", "term", "is_active", "is_published")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (SeasonTeamInline,)

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            if obj.is_active:
                Season.objects.filter(is_active=True).exclude(pk=obj.pk).update(is_active=False)
            super().save_model(request, obj, form, change)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(SeasonTeam)
class SeasonTeamAdmin(admin.ModelAdmin):
    list_display = ("name", "season", "team", "display_order")
    list_filter = ("season",)
    search_fields = ("team__name", "display_name", "season__name")


@admin.register(CoachAssignment)
class CoachAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "season_team", "season")
    list_filter = ("season_team__season",)
    search_fields = ("user__username", "user__first_name", "user__last_name", "season_team__team__name")
    autocomplete_fields = ("user", "season_team")

    @admin.display(description="Season")
    def season(self, obj):
        return obj.season_team.season


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("display_name", "rank", "public_profile", "photo")
    list_filter = ("public_profile",)
    search_fields = ("display_name",)
    fields = ("display_name", "photo", "rank", "public_profile")


@admin.register(RosterMembership)
class RosterMembershipAdmin(admin.ModelAdmin):
    list_display = ("player", "season_team", "jersey_number", "position", "status")
    list_filter = ("season_team__season", "status", "position")
    search_fields = ("player__display_name", "season_team__team__name")


class MatchAppearanceInline(admin.TabularInline):
    model = MatchAppearance
    extra = 0
    autocomplete_fields = ("player",)


class MatchEventInline(admin.TabularInline):
    model = MatchEvent
    extra = 0
    autocomplete_fields = ("player",)


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "kickoff_at", "season", "home_team", "away_team", "score_display", "stage", "status"
    )
    list_filter = ("season", "stage", "status", "score_approved_at")
    search_fields = ("home_team__team__name", "away_team__team__name", "round_name")
    autocomplete_fields = ("home_team", "away_team", "score_approved_by")
    inlines = (MatchAppearanceInline, MatchEventInline)
    fieldsets = (
        (None, {"fields": ("season", "home_team", "away_team", "kickoff_at", "venue", "status")}),
        ("Competition", {"fields": ("stage", "round_name")}),
        ("Official result", {"fields": ("home_score", "away_score", "score_approved_at", "score_approved_by")}),
    )

    @admin.display(description="Score")
    def score_display(self, obj):
        if obj.has_approved_score:
            return f"{obj.home_score}–{obj.away_score}"
        return "—"

    def save_model(self, request, obj, form, change):
        if obj.home_score is not None and obj.away_score is not None:
            if not obj.score_approved_at:
                obj.score_approved_at = timezone.now()
            if not obj.score_approved_by_id:
                obj.score_approved_by = request.user
        else:
            obj.score_approved_at = None
            obj.score_approved_by = None
        super().save_model(request, obj, form, change)


@admin.register(ScoreSubmission)
class ScoreSubmissionAdmin(admin.ModelAdmin):
    list_display = ("match", "reporting_team", "home_score", "away_score", "status", "submitted_by", "submitted_at", "is_current")
    list_filter = ("match__season", "status", "is_current")
    search_fields = ("match__home_team__team__name", "match__away_team__team__name", "submitted_by__username")
    readonly_fields = ("match", "reporting_team", "submitted_by", "home_score", "away_score", "status", "submitted_at", "is_current")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ScoreReview)
class ScoreReviewAdmin(admin.ModelAdmin):
    list_display = ("match", "source", "home_score", "away_score", "status", "created_by", "reviewed_by", "created_at")
    list_filter = ("status", "source", "match__season")
    readonly_fields = tuple(field.name for field in ScoreReview._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SeasonRules)
class SeasonRulesAdmin(admin.ModelAdmin):
    list_display = ("title", "season", "updated_at")
    list_filter = ("season",)
    search_fields = ("title", "body", "season__name")


@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    list_display = ("season", "category", "player", "season_team")
    list_filter = ("season", "category")
    search_fields = ("player__display_name", "season_team__team__name", "citation")
    autocomplete_fields = ("player", "season_team")


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ("caption", "season", "taken_on", "is_published", "display_order")
    list_filter = ("season", "is_published")
    search_fields = ("caption",)


@admin.register(PublicContent)
class PublicContentAdmin(admin.ModelAdmin):
    fields = ("about_heading", "about_body", "sponsor_name", "sponsor_url", "sponsor_offer", "contact_email")

    def has_add_permission(self, request):
        return not PublicContent.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
