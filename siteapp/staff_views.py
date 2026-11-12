from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Q

from .forms import PlayerPhotoForm, ReviewDecisionForm, ScoreForm, ScoreSubmissionForm, StaffAuthenticationForm
from .models import (
    CoachAssignment,
    Match,
    MatchEvent,
    Player,
    RosterMembership,
    ScoreReview,
    ScoreReviewPlayerStat,
    ScoreSubmission,
    ScoreSubmissionStat,
    StaffProfile,
)


class StaffLoginView(LoginView):
    template_name = "siteapp/staff/login.html"
    authentication_form = StaffAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return "/staff/"


def _profile(request, role=None):
    try:
        profile = request.user.staff_profile
    except StaffProfile.DoesNotExist as exc:
        raise PermissionDenied("This account is not assigned a league staff role.") from exc
    if role and profile.role != role:
        raise PermissionDenied("You do not have access to this staff area.")
    return profile


@login_required
def staff_home(request):
    profile = _profile(request)
    if profile.role == StaffProfile.Role.ADMIN:
        return redirect("staff_admin")
    return redirect("staff_coach")


def _create_score_review(match, reports, user, source, home_score=None, away_score=None):
    if home_score is None:
        home_score, away_score = reports[0].home_score, reports[0].away_score
    review = ScoreReview.objects.create(
        match=match,
        source=source,
        home_score=home_score,
        away_score=away_score,
        created_by=user,
    )
    totals = {}
    for report in reports:
        for stat in report.player_stats.all():
            counts = totals.setdefault(stat.player_id, {"goals": 0, "assists": 0})
            counts["goals"] += stat.goals
            counts["assists"] += stat.assists
    ScoreReviewPlayerStat.objects.bulk_create([
        ScoreReviewPlayerStat(review=review, player_id=player_id, **counts)
        for player_id, counts in totals.items()
        if counts["goals"] or counts["assists"]
    ])
    return review


@login_required
def coach_dashboard(request):
    _profile(request, StaffProfile.Role.COACH)
    assignments = CoachAssignment.objects.filter(user=request.user).select_related(
        "season_team__season", "season_team__team"
    )
    assigned_team_ids = list(assignments.values_list("season_team_id", flat=True))
    matches = Match.objects.filter(
        Q(home_team_id__in=assigned_team_ids) | Q(away_team_id__in=assigned_team_ids)
    ).select_related(
        "season", "home_team__team", "away_team__team"
    ).prefetch_related(
        "score_submissions__player_stats", "score_reviews__player_stats", "score_reviews"
    )
    cards = {"unsubmitted": [], "pending": [], "submitted": []}
    now = timezone.now()
    for match in matches:
        submissions = list(match.score_submissions.all())
        submitted_by_team = {
            report.reporting_team_id: report
            for report in submissions
            if report.status == ScoreSubmission.Status.SUBMITTED and report.is_current
        }
        pending_by_team = {
            report.reporting_team_id: report
            for report in submissions
            if report.status == ScoreSubmission.Status.PENDING
        }
        reports = list(submitted_by_team.values())
        reviews = list(match.score_reviews.all())
        has_pending_draft = any(s.status == ScoreSubmission.Status.PENDING for s in submissions)
        disagree = not has_pending_draft and len(reports) == 2 and (reports[0].home_score, reports[0].away_score) != (
            reports[1].home_score, reports[1].away_score
        )
        team_forms = []
        team_reports = []
        submission_statuses = []
        for team in (match.home_team, match.away_team):
            draft = pending_by_team.get(team.pk)
            submitted = submitted_by_team.get(team.pk)
            display_report = draft or submitted
            state = "pending" if draft else "submitted" if submitted else "unsubmitted"
            submission_statuses.append({
                "team": team,
                "state": state,
                "submitted": state == "submitted",
                "label": state.title(),
            })
            if display_report:
                team_reports.append({"team": team, "submission": display_report, "state": state})
            if team.pk not in assigned_team_ids:
                continue
            if draft and draft.submitted_by_id != request.user.pk:
                continue
            if not draft and submitted and submitted.submitted_by_id != request.user.pk:
                continue
            form_submission = draft or (submitted if submitted and submitted.submitted_by_id == request.user.pk else None)
            form_state = "pending" if draft else "resubmit" if form_submission else "new"
            existing_stats = {
                stat.player_id: stat for stat in form_submission.player_stats.all()
            } if form_submission else {}
            roster = RosterMembership.objects.filter(
                season_team=team,
                status__in=(RosterMembership.Status.ACTIVE, RosterMembership.Status.SUBSTITUTE),
            ).select_related("player")
            team_forms.append({
                "team": team,
                "form_state": form_state,
                "submission_id": draft.pk if draft else None,
                "home_score": form_submission.home_score if form_submission else "",
                "away_score": form_submission.away_score if form_submission else "",
                "players": [
                    {
                        "player": member.player,
                        "goals_name": f"goals_{member.player_id}",
                        "assists_name": f"assists_{member.player_id}",
                        "goals": existing_stats.get(member.player_id).goals if member.player_id in existing_stats else 0,
                        "assists": existing_stats.get(member.player_id).assists if member.player_id in existing_stats else 0,
                    }
                    for member in roster
                ],
            })
        card = {
            "match": match,
            "reports": reports,
            "team_reports": team_reports,
            "disagree": disagree,
            "pending_review": any(r.status == ScoreReview.Status.PENDING for r in reviews),
            "latest_review": reviews[-1] if reviews else None,
            "team_forms": team_forms,
            "submission_statuses": submission_statuses,
            "can_report": match.kickoff_at <= now and match.status != Match.Status.CANCELLED,
            "category": (
                "pending" if any(pending_by_team.get(team_id) for team_id in assigned_team_ids)
                else "submitted" if any(submitted_by_team.get(team_id) for team_id in assigned_team_ids)
                else "unsubmitted"
            ),
            "select_label": (
                f"{match.kickoff_at:%b %-d} · {match.home_team.name} vs {match.away_team.name}"
                f"{' · Future' if match.kickoff_at > now else ''}"
            ),
        }
        cards[card["category"]].append(card)
    groups = [
        {"key": key, "label": label, "games": cards[key]}
        for key, label in (("unsubmitted", "Unsubmitted"), ("pending", "Pending"), ("submitted", "Submitted"))
        if cards[key]
    ]
    all_cards = [card for group in groups for card in group["games"]]
    selected_card = next((card for card in all_cards if str(card["match"].pk) == request.GET.get("game")), None)
    if not selected_card and all_cards:
        selected_card = all_cards[0]
    return render(request, "siteapp/staff/coach_dashboard.html", {
        "game_groups": groups,
        "selected_card": selected_card,
    })


@login_required
@require_POST
def submit_score(request, match_id):
    _profile(request, StaffProfile.Role.COACH)
    match = get_object_or_404(Match.objects.select_related("home_team", "away_team"), pk=match_id)
    if match.kickoff_at > timezone.now() or match.status == Match.Status.CANCELLED:
        messages.error(request, "Scores can be reported only after a match has been played.")
        return redirect("staff_coach")
    assigned = CoachAssignment.objects.filter(
        user=request.user,
        season_team_id__in=(match.home_team_id, match.away_team_id),
    ).select_related("season_team")
    allowed_team_ids = list(assigned.values_list("season_team_id", flat=True))
    try:
        reporting_team_id = int(request.POST.get("reporting_team", ""))
    except ValueError as exc:
        raise PermissionDenied("Select one of your assigned teams in this match.") from exc
    if reporting_team_id not in allowed_team_ids:
        raise PermissionDenied("You can only report a score for a team assigned to you.")
    reporting_team = assigned.get(season_team_id=reporting_team_id).season_team
    pending = ScoreSubmission.objects.filter(
        match=match, reporting_team_id=reporting_team_id, status=ScoreSubmission.Status.PENDING
    ).select_related("submitted_by").first()
    current_report = ScoreSubmission.objects.filter(
        match=match, reporting_team_id=reporting_team_id,
        status=ScoreSubmission.Status.SUBMITTED, is_current=True,
    ).select_related("submitted_by").first()
    if pending and pending.submitted_by_id != request.user.pk:
        raise PermissionDenied("Only the coach who created this pending report can edit or submit it.")
    if not pending and current_report and current_report.submitted_by_id != request.user.pk:
        raise PermissionDenied("Only the coach who submitted this report can create a resubmission.")
    action = request.POST.get("action")
    if action not in {"save_pending", "submit"}:
        raise PermissionDenied("Choose whether to save a pending report or submit it.")
    if action == "submit" and not pending:
        raise PermissionDenied("Save a pending report before submitting it.")
    form = ScoreSubmissionForm(request.POST, team=reporting_team, match=match)
    if not form.is_valid():
        messages.error(request, "Enter both scores as whole numbers from 0 to 99.")
        return redirect("staff_coach")

    with transaction.atomic():
        submission = pending or ScoreSubmission(
            match=match,
            reporting_team_id=reporting_team_id,
            submitted_by=request.user,
            status=ScoreSubmission.Status.PENDING,
            is_current=False,
        )
        submission.home_score = form.cleaned_data["home_score"]
        submission.away_score = form.cleaned_data["away_score"]
        submission.save()
        submission.player_stats.all().delete()
        ScoreSubmissionStat.objects.bulk_create([
            ScoreSubmissionStat(submission=submission, **stat)
            for stat in form.get_player_stats()
        ])
        if action == "submit":
            now = timezone.now()
            if current_report:
                current_report.is_current = False
                current_report.save(update_fields=("is_current",))
            match.score_reviews.filter(status=ScoreReview.Status.PENDING).update(
                status=ScoreReview.Status.SUPERSEDED,
                reviewed_at=now,
                decision_note="Superseded because a coach submitted a new score report.",
            )
            submission.status = ScoreSubmission.Status.SUBMITTED
            submission.is_current = True
            submission.submitted_at = now
            submission.save(update_fields=("status", "is_current", "submitted_at"))
            reports = list(
                ScoreSubmission.objects.filter(
                    match=match, status=ScoreSubmission.Status.SUBMITTED, is_current=True
                ).prefetch_related("player_stats").order_by("reporting_team_id")
            )
            if len(reports) == 2 and (reports[0].home_score, reports[0].away_score) == (
                reports[1].home_score, reports[1].away_score
            ) and not match.score_reviews.filter(status=ScoreReview.Status.PENDING).exists():
                _create_score_review(match, reports, request.user, ScoreReview.Source.MATCHED_REPORTS)
            if len(reports) < 2:
                messages.success(request, "Report submitted. It will enter result review when the other team submits.")
            elif reports[0].home_score != reports[1].home_score or reports[0].away_score != reports[1].away_score:
                messages.warning(request, "Report submitted. The team scores differ; coaches can reconcile them.")
            else:
                messages.success(request, "Both team reports match and are waiting for administrator approval.")
        else:
            messages.success(request, "Report saved as pending. Submit it when it is ready, or cancel it.")
    return redirect(f"/staff/coach/?game={match.pk}")


@login_required
@require_POST
def cancel_score_submission(request, match_id):
    _profile(request, StaffProfile.Role.COACH)
    match = get_object_or_404(Match, pk=match_id)
    try:
        team_id = int(request.POST.get("reporting_team", ""))
    except ValueError as exc:
        raise PermissionDenied("Choose your assigned team.") from exc
    if not CoachAssignment.objects.filter(user=request.user, season_team_id=team_id).exists():
        raise PermissionDenied("You can only cancel a report for your assigned team.")
    pending = get_object_or_404(
        ScoreSubmission,
        match=match,
        reporting_team_id=team_id,
        status=ScoreSubmission.Status.PENDING,
        submitted_by=request.user,
    )
    pending.delete()
    messages.success(request, "Pending report cancelled.")
    return redirect(f"/staff/coach/?game={match.pk}")


@login_required
@require_POST
def submit_reconciliation(request, match_id):
    _profile(request, StaffProfile.Role.COACH)
    match = get_object_or_404(Match, pk=match_id)
    if match.kickoff_at > timezone.now() or match.status == Match.Status.CANCELLED:
        messages.error(request, "Scores can be reconciled only after a match has been played.")
        return redirect("staff_coach")
    has_assignment = CoachAssignment.objects.filter(
        user=request.user, season_team_id__in=(match.home_team_id, match.away_team_id)
    ).exists()
    if not has_assignment:
        raise PermissionDenied("You must be assigned to a team in this match to reconcile its score.")
    if ScoreSubmission.objects.filter(match=match, status=ScoreSubmission.Status.PENDING).exists():
        messages.error(request, "Submit or cancel each pending team report before reconciling the score.")
        return redirect(f"/staff/coach/?game={match.pk}")
    reports = list(ScoreSubmission.objects.filter(
        match=match, status=ScoreSubmission.Status.SUBMITTED, is_current=True
    ).prefetch_related("player_stats"))
    if len(reports) != 2 or (reports[0].home_score, reports[0].away_score) == (
        reports[1].home_score, reports[1].away_score
    ):
        messages.error(request, "Reconciliation is available only when both teams have submitted different scores.")
        return redirect("staff_coach")
    form = ScoreForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a valid home and away score.")
        return redirect("staff_coach")
    if match.score_reviews.filter(status=ScoreReview.Status.PENDING).exists():
        messages.error(request, "This match already has a result waiting for administrator review.")
        return redirect("staff_coach")
    _create_score_review(
        match, reports, request.user, ScoreReview.Source.COACH_RECONCILIATION,
        home_score=form.cleaned_data["home_score"],
        away_score=form.cleaned_data["away_score"],
    )
    messages.success(request, "Reconciled score sent to an administrator for approval.")
    return redirect("staff_coach")


@login_required
def admin_dashboard(request):
    _profile(request, StaffProfile.Role.ADMIN)
    reviews = ScoreReview.objects.filter(status=ScoreReview.Status.PENDING).select_related(
        "match__season", "match__home_team__team", "match__away_team__team", "created_by"
    ).prefetch_related(
        "player_stats__player", "match__score_submissions__reporting_team__team",
        "match__score_submissions__player_stats__player",
    )
    return render(request, "siteapp/staff/admin_dashboard.html", {"reviews": reviews})


@login_required
def photo_dashboard(request):
    profile = _profile(request)
    players = Player.objects.filter(roster_memberships__season_team__season__is_active=True).distinct()
    if profile.role == StaffProfile.Role.COACH:
        players = players.filter(roster_memberships__season_team__coach_assignments__user=request.user)
    return render(request, "siteapp/staff/photos.html", {"players": players.order_by("display_name")})


@login_required
@require_POST
def decide_score_review(request, review_id):
    _profile(request, StaffProfile.Role.ADMIN)
    with transaction.atomic():
        review = get_object_or_404(
            ScoreReview.objects.select_for_update().select_related("match"), pk=review_id
        )
        if review.status != ScoreReview.Status.PENDING:
            messages.error(request, "This review has already been decided.")
            return redirect("staff_admin")
        form = ReviewDecisionForm(request.POST, initial={
            "home_score": review.home_score,
            "away_score": review.away_score,
        })
        if not form.is_valid():
            messages.error(request, "Enter valid scores and choose approve or reject.")
            return redirect("staff_admin")
        now = timezone.now()
        review.reviewed_by = request.user
        review.reviewed_at = now
        review.decision_note = form.cleaned_data["note"]
        if form.cleaned_data["action"] == "approve":
            review.status = ScoreReview.Status.APPROVED
            review.home_score = form.cleaned_data["home_score"]
            review.away_score = form.cleaned_data["away_score"]
            review.match.home_score = review.home_score
            review.match.away_score = review.away_score
            review.match.score_approved_at = now
            review.match.score_approved_by = request.user
            review.match.save(update_fields=(
                "home_score", "away_score", "score_approved_at", "score_approved_by", "updated_at"
            ))
            MatchEvent.objects.filter(match=review.match, source_score_review__isnull=False).delete()
            events = []
            for stat in review.player_stats.all():
                events.extend(
                    MatchEvent(match=review.match, player=stat.player, kind=MatchEvent.Kind.GOAL,
                               source_score_review=review)
                    for _ in range(stat.goals)
                )
                events.extend(
                    MatchEvent(match=review.match, player=stat.player, kind=MatchEvent.Kind.ASSIST,
                               source_score_review=review)
                    for _ in range(stat.assists)
                )
            MatchEvent.objects.bulk_create(events)
            messages.success(request, "Official result approved and published.")
        else:
            review.status = ScoreReview.Status.REJECTED
            messages.success(request, "Result rejected. Coaches can submit corrected reports.")
        review.save(update_fields=(
            "status", "home_score", "away_score", "reviewed_by", "reviewed_at", "decision_note"
        ))
    return redirect("staff_admin")


@login_required
@require_POST
def update_player_photo(request, player_id):
    profile = _profile(request)
    player = get_object_or_404(Player, pk=player_id)
    if profile.role == StaffProfile.Role.COACH:
        assigned_roster = RosterMembership.objects.filter(
            player=player,
            season_team__coach_assignments__user=request.user,
        ).exists()
        if not assigned_roster:
            raise PermissionDenied("You can only update photos for players on your assigned teams.")
    form = PlayerPhotoForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Choose a valid image smaller than 8 MB.")
        return redirect("staff_coach" if profile.role == StaffProfile.Role.COACH else "staff_admin")
    player.photo = form.cleaned_data["photo"]
    player.save(update_fields=("photo",))
    messages.success(request, f"Photo updated for {player.display_name}.")
    return redirect("staff_coach" if profile.role == StaffProfile.Role.COACH else "staff_admin")
