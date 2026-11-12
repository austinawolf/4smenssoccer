from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.text import slugify


def default_tie_breakers():
    return ["head_to_head", "goal_difference", "goals_against", "clean_sheets"]


class PublicContent(models.Model):
    key = models.CharField(max_length=20, unique=True, default="main", editable=False)
    about_heading = models.CharField(max_length=160, default="Good soccer. Good people.")
    about_body = models.TextField(
        default="11 v 11 men's league established in 2005. Players must meet the season age requirements. "
        "New players attend a pre-season scrimmage so managers can build balanced teams."
    )
    sponsor_name = models.CharField(max_length=160, blank=True)
    sponsor_url = models.URLField(blank=True)
    sponsor_offer = models.CharField(max_length=240, blank=True)
    contact_email = models.EmailField(blank=True)

    class Meta:
        verbose_name = "homepage and sponsor content"
        verbose_name_plural = "homepage and sponsor content"

    def __str__(self):
        return "Homepage and sponsor content"


class Season(models.Model):
    class Term(models.TextChoices):
        SPRING = "spring", "Spring"
        FALL = "fall", "Fall"
        OTHER = "other", "Other"

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    year = models.PositiveSmallIntegerField()
    term = models.CharField(max_length=12, choices=Term.choices, default=Term.OTHER)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False, help_text="Default season shown on public pages.")
    is_published = models.BooleanField(default=True)
    points_for_win = models.PositiveSmallIntegerField(default=3)
    points_for_draw = models.PositiveSmallIntegerField(default=1)
    points_for_loss = models.PositiveSmallIntegerField(default=0)
    tie_breakers = models.JSONField(default=default_tie_breakers, blank=True)

    class Meta:
        ordering = ("-year", "-term", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("is_active",),
                condition=Q(is_active=True),
                name="only_one_active_season",
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "The season end date must be after its start date."})
        if self.is_active and not self.is_published:
            raise ValidationError({"is_active": "The active season must be published."})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Team(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    badge = models.ImageField(upload_to="teams/", blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class SeasonTeam(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="season_teams")
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="season_entries")
    display_name = models.CharField(max_length=120, blank=True, help_text="Optional season-specific team name.")
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "display_name", "team__name")
        constraints = [
            models.UniqueConstraint(fields=("season", "team"), name="unique_team_per_season"),
        ]

    def __str__(self):
        return self.name

    @property
    def name(self):
        return self.display_name or self.team.name


class StaffProfile(models.Model):
    class Role(models.TextChoices):
        COACH = "coach", "Coach"
        ADMIN = "admin", "League administrator"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile")
    role = models.CharField(max_length=12, choices=Role.choices)

    def __str__(self):
        return f"{self.user} ({self.get_role_display()})"


class CoachAssignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coach_assignments")
    season_team = models.ForeignKey(SeasonTeam, on_delete=models.CASCADE, related_name="coach_assignments")

    class Meta:
        ordering = ("season_team__season", "season_team__display_order", "season_team__team__name")
        constraints = [
            models.UniqueConstraint(fields=("user", "season_team"), name="unique_coach_per_season_team"),
        ]

    def __str__(self):
        return f"{self.user} — {self.season_team}"


class Player(models.Model):
    display_name = models.CharField(max_length=120)
    photo = models.ImageField(upload_to="players/", blank=True)
    rank = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Private internal player assessment. Never shown on public pages.",
    )
    public_profile = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_name",)

    def __str__(self):
        return self.display_name


class RosterMembership(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUBSTITUTE = "substitute", "Substitute"
        INACTIVE = "inactive", "Inactive"

    class Position(models.TextChoices):
        GOALKEEPER = "goalkeeper", "Goalkeeper"
        DEFENDER = "defender", "Defender"
        MIDFIELDER = "midfielder", "Midfielder"
        FORWARD = "forward", "Forward"
        OTHER = "other", "Other"

    season_team = models.ForeignKey(SeasonTeam, on_delete=models.CASCADE, related_name="roster")
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="roster_memberships")
    jersey_number = models.PositiveSmallIntegerField(null=True, blank=True)
    position = models.CharField(max_length=12, choices=Position.choices, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ("jersey_number", "player__display_name")
        constraints = [
            models.UniqueConstraint(fields=("season_team", "player"), name="player_once_per_season_team"),
        ]

    def __str__(self):
        return f"{self.player} — {self.season_team}"

    def clean(self):
        if not self.season_team_id or not self.player_id:
            return
        duplicate = RosterMembership.objects.filter(
            season_team__season_id=self.season_team.season_id,
            player_id=self.player_id,
        ).exclude(pk=self.pk)
        if duplicate.exists():
            raise ValidationError({"player": "This player is already assigned to a team in this season."})


class Match(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        POSTPONED = "postponed", "Postponed"
        CANCELLED = "cancelled", "Cancelled"

    class Stage(models.TextChoices):
        REGULAR = "regular", "Regular season"
        PLAYOFF = "playoff", "Playoffs"

    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="matches")
    home_team = models.ForeignKey(SeasonTeam, on_delete=models.PROTECT, related_name="home_matches")
    away_team = models.ForeignKey(SeasonTeam, on_delete=models.PROTECT, related_name="away_matches")
    kickoff_at = models.DateTimeField()
    venue = models.CharField(max_length=180, default="4S Ranch Sports Park")
    stage = models.CharField(max_length=12, choices=Stage.choices, default=Stage.REGULAR)
    round_name = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)
    home_score = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    away_score = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    score_approved_at = models.DateTimeField(null=True, blank=True)
    score_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_match_scores",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("kickoff_at", "pk")
        constraints = [
            models.CheckConstraint(condition=~Q(home_team=F("away_team")), name="match_teams_are_different"),
        ]

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} ({self.kickoff_at:%Y-%m-%d})"

    @property
    def has_approved_score(self):
        return (
            self.score_approved_at is not None
            and self.home_score is not None
            and self.away_score is not None
        )

    def clean(self):
        errors = {}
        if self.home_team_id and self.away_team_id and self.home_team_id == self.away_team_id:
            errors["away_team"] = "A team cannot play itself."
        for field in ("home_team", "away_team"):
            season_team = getattr(self, field, None)
            if season_team and self.season_id and season_team.season_id != self.season_id:
                errors[field] = "Both teams must be registered in the match season."
        if (self.home_score is None) != (self.away_score is None):
            errors["away_score"] = "Enter both scores, or leave both empty."
        if self.score_approved_at and (self.home_score is None or self.away_score is None):
            errors["score_approved_at"] = "An approved result must include both scores."
        if errors:
            raise ValidationError(errors)


class ScoreSubmission(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUBMITTED = "submitted", "Submitted"

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="score_submissions")
    reporting_team = models.ForeignKey(SeasonTeam, on_delete=models.PROTECT, related_name="score_submissions")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="score_submissions")
    home_score = models.PositiveSmallIntegerField(validators=[MinValueValidator(0)])
    away_score = models.PositiveSmallIntegerField(validators=[MinValueValidator(0)])
    submitted_at = models.DateTimeField(default=timezone.now)
    is_current = models.BooleanField(default=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SUBMITTED)

    class Meta:
        ordering = ("submitted_at", "pk")
        indexes = [models.Index(fields=("match", "is_current"))]
        constraints = [
            models.UniqueConstraint(
                fields=("match", "reporting_team"),
                condition=Q(status="pending"),
                name="one_pending_submission_per_team",
            ),
            models.UniqueConstraint(
                fields=("match", "reporting_team"),
                condition=Q(status="submitted", is_current=True),
                name="one_current_submission_per_team",
            ),
            models.CheckConstraint(
                condition=Q(status="submitted") | Q(is_current=False),
                name="pending_submission_not_current",
            ),
        ]

    def __str__(self):
        return f"{self.match}: {self.home_score}–{self.away_score} ({self.reporting_team})"

    def clean(self):
        if self.match_id and self.reporting_team_id:
            if self.reporting_team_id not in (self.match.home_team_id, self.match.away_team_id):
                raise ValidationError({"reporting_team": "The reporting team must be playing in this match."})
            if self.reporting_team.season_id != self.match.season_id:
                raise ValidationError({"reporting_team": "The reporting team must belong to the match season."})


class ScoreReview(models.Model):
    class Source(models.TextChoices):
        MATCHED_REPORTS = "matched", "Matching coach reports"
        COACH_RECONCILIATION = "reconciled", "Coach reconciliation"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SUPERSEDED = "superseded", "Superseded by a new report"

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="score_reviews")
    source = models.CharField(max_length=12, choices=Source.choices)
    home_score = models.PositiveSmallIntegerField(validators=[MinValueValidator(0)])
    away_score = models.PositiveSmallIntegerField(validators=[MinValueValidator(0)])
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_score_reviews")
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="decided_score_reviews"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        ordering = ("created_at", "pk")

    def __str__(self):
        return f"{self.match}: {self.home_score}–{self.away_score} ({self.get_status_display()})"


class ScoreSubmissionStat(models.Model):
    submission = models.ForeignKey(ScoreSubmission, on_delete=models.CASCADE, related_name="player_stats")
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="score_submission_stats")
    goals = models.PositiveSmallIntegerField(default=0)
    assists = models.PositiveSmallIntegerField(default=0)
    yellow_cards = models.PositiveSmallIntegerField(default=0)
    red_cards = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("submission", "player"), name="one_player_stat_per_submission"),
            models.CheckConstraint(condition=Q(goals__gt=0) | Q(assists__gt=0) | Q(yellow_cards__gt=0) | Q(red_cards__gt=0), name="score_stat_has_contribution"),
        ]

    def clean(self):
        if self.submission_id and self.player_id and not RosterMembership.objects.filter(
            season_team=self.submission.reporting_team, player=self.player
        ).exclude(status=RosterMembership.Status.INACTIVE).exists():
            raise ValidationError({"player": "Player must be on the reporting team's active roster."})


class ScoreReviewPlayerStat(models.Model):
    review = models.ForeignKey(ScoreReview, on_delete=models.CASCADE, related_name="player_stats")
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="score_review_stats")
    goals = models.PositiveSmallIntegerField(default=0)
    assists = models.PositiveSmallIntegerField(default=0)
    yellow_cards = models.PositiveSmallIntegerField(default=0)
    red_cards = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("review", "player"), name="one_player_stat_per_review"),
            models.CheckConstraint(condition=Q(goals__gt=0) | Q(assists__gt=0) | Q(yellow_cards__gt=0) | Q(red_cards__gt=0), name="review_stat_has_contribution"),
        ]

    def clean(self):
        if self.review_id and self.player_id:
            match = self.review.match
            eligible = RosterMembership.objects.filter(
                season_team__in=(match.home_team, match.away_team), player=self.player
            ).exclude(status=RosterMembership.Status.INACTIVE).exists()
            if not eligible:
                raise ValidationError({"player": "Player must be on one of the teams in this match."})


class MatchAppearance(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="appearances")
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="match_appearances")
    minutes_played = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("player__display_name",)
        constraints = [
            models.UniqueConstraint(fields=("match", "player"), name="player_once_per_match"),
        ]

    def __str__(self):
        return f"{self.player} — {self.match}"

    def clean(self):
        if self.match_id and self.player_id:
            eligible = RosterMembership.objects.filter(
                season_team__season=self.match.season,
                season_team__in=(self.match.home_team, self.match.away_team),
                player=self.player,
            ).exists()
            if not eligible:
                raise ValidationError({"player": "The player must be on one of the teams in this match."})


class MatchEvent(models.Model):
    class Kind(models.TextChoices):
        GOAL = "goal", "Goal"
        ASSIST = "assist", "Assist"
        YELLOW_CARD = "yellow", "Yellow card"
        RED_CARD = "red", "Red card"

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="events")
    source_score_review = models.ForeignKey(
        ScoreReview, null=True, blank=True, on_delete=models.SET_NULL, related_name="published_events"
    )
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="match_events")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    minute = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ("match__kickoff_at", "minute", "pk")

    def __str__(self):
        return f"{self.get_kind_display()} — {self.player}"

    def clean(self):
        if self.match_id and self.player_id:
            eligible = RosterMembership.objects.filter(
                season_team__season=self.match.season,
                season_team__in=(self.match.home_team, self.match.away_team),
                player=self.player,
            ).exists()
            if not eligible:
                raise ValidationError({"player": "The player must be on one of the teams in this match."})


class SeasonRules(models.Model):
    season = models.OneToOneField(Season, on_delete=models.CASCADE, related_name="rules")
    title = models.CharField(max_length=160, default="League Rules")
    body = models.TextField()
    updated_at = models.DateField(default=timezone.localdate)

    class Meta:
        verbose_name = "season rules"
        verbose_name_plural = "season rules"

    def __str__(self):
        return f"{self.title} — {self.season}"


class Award(models.Model):
    class Category(models.TextChoices):
        CHAMPION = "champion", "League champions"
        RUNNER_UP = "runner_up", "Runner-up"
        MVP = "mvp", "MVP"
        GOLDEN_BOOT = "golden_boot", "Golden Boot"
        GOLDEN_GLOVES = "golden_gloves", "Golden Gloves"
        OTHER = "other", "Other"

    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="awards")
    category = models.CharField(max_length=20, choices=Category.choices)
    player = models.ForeignKey(Player, null=True, blank=True, on_delete=models.PROTECT, related_name="awards")
    season_team = models.ForeignKey(
        SeasonTeam,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="awards",
    )
    citation = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ("season__year", "category", "player__display_name", "season_team__team__name")

    def __str__(self):
        return f"{self.get_category_display()} — {self.season}"

    def clean(self):
        if bool(self.player_id) == bool(self.season_team_id):
            raise ValidationError("Select exactly one player or team as the award recipient.")
        if self.season_team_id and self.season_id and self.season_team.season_id != self.season_id:
            raise ValidationError({"season_team": "The team must participate in the award season."})


class GalleryItem(models.Model):
    season = models.ForeignKey(
        Season,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="gallery_items",
    )
    image = models.ImageField(upload_to="gallery/")
    caption = models.CharField(max_length=240, blank=True)
    taken_on = models.DateField(null=True, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_order", "taken_on", "pk")

    def __str__(self):
        return self.caption or f"Gallery image {self.pk or ''}"
