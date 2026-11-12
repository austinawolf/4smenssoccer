from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from siteapp.models import (
    CoachAssignment,
    Match,
    MatchEvent,
    Player,
    RosterMembership,
    ScoreReview,
    ScoreSubmission,
    Season,
    SeasonTeam,
    StaffProfile,
)
from siteapp.views import get_leaderboard


class CoachStaffWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.season = Season.objects.create(name="Test Fall", year=2026, term="fall", is_active=True)
        cls.home_team = SeasonTeam.objects.create(
            season=cls.season, team_id=cls._make_team("Home United")
        )
        cls.away_team = SeasonTeam.objects.create(
            season=cls.season, team_id=cls._make_team("Away Rovers")
        )
        cls.home_player = Player.objects.create(display_name="Home Scorer")
        cls.away_player = Player.objects.create(display_name="Away Scorer")
        RosterMembership.objects.create(season_team=cls.home_team, player=cls.home_player)
        RosterMembership.objects.create(season_team=cls.away_team, player=cls.away_player)
        cls.home_coach = User.objects.create_user("home-coach", password="test-password")
        cls.away_coach = User.objects.create_user("away-coach", password="test-password")
        cls.home_teammate = User.objects.create_user("home-teammate", password="test-password")
        cls.admin_user = User.objects.create_user("league-admin", password="test-password")
        for user, role in (
            (cls.home_coach, StaffProfile.Role.COACH),
            (cls.away_coach, StaffProfile.Role.COACH),
            (cls.home_teammate, StaffProfile.Role.COACH),
            (cls.admin_user, StaffProfile.Role.ADMIN),
        ):
            StaffProfile.objects.create(user=user, role=role)
        CoachAssignment.objects.create(user=cls.home_coach, season_team=cls.home_team)
        CoachAssignment.objects.create(user=cls.home_teammate, season_team=cls.home_team)
        CoachAssignment.objects.create(user=cls.away_coach, season_team=cls.away_team)
        cls.past_match = Match.objects.create(
            season=cls.season,
            home_team=cls.home_team,
            away_team=cls.away_team,
            kickoff_at=timezone.now() - timedelta(days=1),
        )
        cls.other_past_match = Match.objects.create(
            season=cls.season,
            home_team=cls.home_team,
            away_team=cls.away_team,
            kickoff_at=timezone.now() - timedelta(hours=4),
        )
        cls.future_match = Match.objects.create(
            season=cls.season,
            home_team=cls.home_team,
            away_team=cls.away_team,
            kickoff_at=timezone.now() + timedelta(days=3),
        )

    @staticmethod
    def _make_team(name):
        from siteapp.models import Team
        return Team.objects.create(name=name).pk

    def _login(self, user):
        client = self.client_class()
        client.force_login(user)
        return client

    def _report(self, client, match, team, home, away, stats=None):
        data = {"reporting_team": team.pk, "home_score": home, "away_score": away}
        data.update(stats or {})
        client.post(f"/staff/matches/{match.pk}/report/", {**data, "action": "save_pending"})
        return client.post(f"/staff/matches/{match.pk}/report/", {**data, "action": "submit"})

    def test_dashboard_groups_games_and_only_offers_own_resubmission(self):
        home = self._login(self.home_coach)
        self._report(home, self.past_match, self.home_team, 1, 0)
        home.post(f"/staff/matches/{self.other_past_match.pk}/report/", {
            "action": "save_pending",
            "reporting_team": self.home_team.pk,
            "home_score": 1,
            "away_score": 0,
        })
        page = home.get(f"/staff/coach/?game={self.past_match.pk}")
        content = page.content
        self.assertIn(b'<optgroup label="Unsubmitted">', content)
        self.assertIn(b'<optgroup label="Pending">', content)
        self.assertIn(b'<optgroup label="Submitted">', content)
        self.assertIn(b"Start a resubmission for Home United", content)
        self.assertIn(b"Away Rovers score", content)

        teammate = self.client_class(raise_request_exception=False)
        teammate.force_login(self.home_teammate)
        teammate_page = teammate.get(f"/staff/coach/?game={self.past_match.pk}")
        self.assertNotIn(b"Start a resubmission for Home United", teammate_page.content)
        self.assertContains(teammate_page, "A report is already owned by another coach")
        denied = teammate.post(f"/staff/matches/{self.past_match.pk}/report/", {
            "reporting_team": self.home_team.pk,
            "home_score": 1,
            "away_score": 0,
            "action": "save_pending",
        })
        self.assertEqual(denied.status_code, 403)

    def test_pending_report_can_be_cancelled_or_submitted(self):
        home = self._login(self.home_coach)
        data = {
            "reporting_team": self.home_team.pk,
            "home_score": 1,
            "away_score": 0,
            f"goals_{self.home_player.pk}": 1,
            "action": "save_pending",
        }
        home.post(f"/staff/matches/{self.other_past_match.pk}/report/", data)
        pending = ScoreSubmission.objects.get(match=self.other_past_match)
        self.assertEqual(pending.status, ScoreSubmission.Status.PENDING)
        self.assertFalse(pending.is_current)
        self.assertContains(home.get(f"/staff/coach/?game={self.other_past_match.pk}"), "Cancel pending report")

        home.post(f"/staff/matches/{self.other_past_match.pk}/cancel-report/", {
            "reporting_team": self.home_team.pk,
        })
        self.assertFalse(ScoreSubmission.objects.filter(match=self.other_past_match).exists())

        home.post(f"/staff/matches/{self.other_past_match.pk}/report/", data)
        home.post(f"/staff/matches/{self.other_past_match.pk}/report/", {**data, "action": "submit"})
        submitted = ScoreSubmission.objects.get(match=self.other_past_match)
        self.assertEqual(submitted.status, ScoreSubmission.Status.SUBMITTED)
        self.assertTrue(submitted.is_current)

    def test_approved_score_publishes_player_goal_and_assist_events(self):
        home = self._login(self.home_coach)
        away = self._login(self.away_coach)
        self._report(home, self.past_match, self.home_team, 2, 0, {
            f"goals_{self.home_player.pk}": 2,
            f"assists_{self.home_player.pk}": 1,
        })
        self._report(away, self.past_match, self.away_team, 2, 0)
        review = ScoreReview.objects.get(match=self.past_match, status=ScoreReview.Status.PENDING)
        self.assertEqual(review.player_stats.get(player=self.home_player).goals, 2)
        self.assertIsNone(self.past_match.home_score)

        admin = self._login(self.admin_user)
        self.assertContains(admin.get("/staff/admin/"), "Home Scorer")
        admin.post(f"/staff/reviews/{review.pk}/decision/", {
            "action": "approve", "home_score": 2, "away_score": 0, "note": "Verified",
        })
        self.past_match.refresh_from_db()
        self.assertEqual((self.past_match.home_score, self.past_match.away_score), (2, 0))
        self.assertEqual(MatchEvent.objects.filter(match=self.past_match, kind=MatchEvent.Kind.GOAL).count(), 2)
        self.assertEqual(MatchEvent.objects.filter(match=self.past_match, kind=MatchEvent.Kind.ASSIST).count(), 1)
        row = next(row for row in get_leaderboard(self.season) if row["player"] == self.home_player)
        self.assertEqual((row["goals"], row["assists"]), (2, 1))

    def test_matching_team_reports_merge_stats_from_both_rosters(self):
        home = self._login(self.home_coach)
        away = self._login(self.away_coach)
        self._report(home, self.past_match, self.home_team, 1, 1, {
            f"goals_{self.home_player.pk}": 1,
            f"assists_{self.home_player.pk}": 1,
        })
        self._report(away, self.past_match, self.away_team, 1, 1, {
            f"goals_{self.away_player.pk}": 1,
        })
        review = ScoreReview.objects.get(match=self.past_match, status=ScoreReview.Status.PENDING)
        stats = {row.player_id: (row.goals, row.assists) for row in review.player_stats.all()}
        self.assertEqual(stats, {self.home_player.pk: (1, 1), self.away_player.pk: (1, 0)})

        admin = self._login(self.admin_user)
        admin.post(f"/staff/reviews/{review.pk}/decision/", {
            "action": "approve", "home_score": 1, "away_score": 1, "note": "Both teams reported",
        })
        self.assertEqual(MatchEvent.objects.filter(
            match=self.past_match, kind=MatchEvent.Kind.GOAL
        ).count(), 2)

    def test_resubmitting_replaces_pending_review_and_uses_updated_stats(self):
        home = self._login(self.home_coach)
        away = self._login(self.away_coach)
        self._report(home, self.past_match, self.home_team, 2, 0, {f"goals_{self.home_player.pk}": 2})
        self._report(away, self.past_match, self.away_team, 2, 0)
        first_review = ScoreReview.objects.get(match=self.past_match, status=ScoreReview.Status.PENDING)
        self._report(home, self.past_match, self.home_team, 2, 0, {
            f"goals_{self.home_player.pk}": 1,
            f"assists_{self.home_player.pk}": 1,
        })
        first_review.refresh_from_db()
        self.assertEqual(first_review.status, ScoreReview.Status.SUPERSEDED)
        next_review = ScoreReview.objects.get(match=self.past_match, status=ScoreReview.Status.PENDING)
        current_stat = next_review.player_stats.get(player=self.home_player)
        self.assertEqual((current_stat.goals, current_stat.assists), (1, 1))

    def test_reconciliation_carries_reported_player_stats_into_approval(self):
        home = self._login(self.home_coach)
        away = self._login(self.away_coach)
        self._report(home, self.past_match, self.home_team, 1, 0, {
            f"goals_{self.home_player.pk}": 1,
            f"assists_{self.home_player.pk}": 1,
        })
        self._report(away, self.past_match, self.away_team, 0, 0)
        response = home.post(f"/staff/matches/{self.past_match.pk}/reconcile/", {
            "home_score": 1,
            "away_score": 0,
        })
        self.assertEqual(response.status_code, 302)
        review = ScoreReview.objects.get(match=self.past_match, status=ScoreReview.Status.PENDING)
        self.assertEqual(review.source, ScoreReview.Source.COACH_RECONCILIATION)
        self.assertEqual(review.player_stats.get(player=self.home_player).assists, 1)

        admin = self._login(self.admin_user)
        admin.post(f"/staff/reviews/{review.pk}/decision/", {
            "action": "approve", "home_score": 1, "away_score": 0, "note": "Agreed",
        })
        self.assertEqual(MatchEvent.objects.filter(
            match=self.past_match, kind=MatchEvent.Kind.GOAL, player=self.home_player
        ).count(), 1)
        self.assertEqual(MatchEvent.objects.filter(
            match=self.past_match, kind=MatchEvent.Kind.ASSIST, player=self.home_player
        ).count(), 1)
