from django.contrib import admin
from django.db import transaction
from django.utils import timezone

from .models import (
    Award,
    GalleryItem,
    Match,
    MatchAppearance,
    MatchEvent,
    Player,
    RosterMembership,
    Season,
    SeasonRules,
    SeasonTeam,
    Team,
)


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
