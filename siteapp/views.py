from collections import defaultdict

from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import render

from .models import (
    Award,
    GalleryItem,
    Match,
    MatchEvent,
    Player,
    Season,
    SeasonRules,
    SeasonTeam,
)

SECTIONS = {
    "home": ("Home", "4S Ranch Men's Soccer League", "League information and season updates."),
    "teams": ("Teams", "Teams", "Browse teams and season rosters."),
    "schedule": ("Schedule", "Schedule", "View upcoming games and approved results."),
    "standings": ("Standings", "Standings", "Follow the season table and player leaderboard."),
    "coaches": ("Coaches", "Coaches", "Privileged coaches will sign in here to report match scores."),
    "admin": ("Admin", "Admin", "League administrators manage seasons and review reported scores."),
    "rules": ("Rules", "Rules", "Read the current league rules."),
    "awards": ("Champions & Awards", "Champions & Awards", "Season champions and individual awards."),
    "gallery": ("Gallery", "Gallery", "Photos from the league's seasons."),
}

# Team badges published by the previous site (Fall 2026 directory).
LEGACY_TEAM_BADGES = {
    "grassholes": "https://4smenssoccer.com/wp-content/uploads/2026/08/IMG-20260830-WA0006.jpg",
    "pinkponyclubdefutbol": "https://4smenssoccer.com/wp-content/uploads/2026/08/IMG-20260830-WA0011.jpg",
    "hufflepufffc": "https://4smenssoccer.com/wp-content/uploads/2026/08/IMG-20260830-WA0009.jpg",
    "seaurchins": "https://4smenssoccer.com/wp-content/uploads/2026/08/IMG-20260830-WA0005.jpg",
    "purpletippedcobras": "https://4smenssoccer.com/wp-content/uploads/2026/08/IMG-20260830-WA0008.jpg",
    "smurfturf": "https://4smenssoccer.com/wp-content/uploads/2026/08/IMG-20260830-WA0010.jpg",
    "upyourarsenal": "https://4smenssoccer.com/wp-content/uploads/2026/08/IMG-20260830-WA0007.jpg",
}


def get_selected_season(request):
    seasons = Season.objects.filter(is_published=True)
    requested_slug = request.GET.get("season")
    if requested_slug:
        return seasons.filter(slug=requested_slug).first()
    return seasons.filter(is_active=True).first() or seasons.order_by("-year", "-start_date").first()


def get_standings(season):
    if season is None:
        return []
    teams = list(SeasonTeam.objects.filter(season=season).select_related("team"))
    rows = {
        team.pk: {
            "team": team, "played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0, "goal_difference": 0,
            "points": 0, "clean_sheets": 0, "head_to_head_points": 0,
        }
        for team in teams
    }
    matches = Match.objects.filter(
        season=season,
        stage=Match.Stage.REGULAR,
        score_approved_at__isnull=False,
        home_score__isnull=False,
        away_score__isnull=False,
    ).select_related("home_team", "away_team")
    match_rows = []
    for match in matches:
        home, away = rows.get(match.home_team_id), rows.get(match.away_team_id)
        if home is None or away is None:
            continue
        hs, aws = match.home_score, match.away_score
        for row, scored, conceded in ((home, hs, aws), (away, aws, hs)):
            row["played"] += 1
            row["goals_for"] += scored
            row["goals_against"] += conceded
            row["clean_sheets"] += conceded == 0
        if hs > aws:
            home["wins"] += 1
            away["losses"] += 1
            home["points"] += season.points_for_win
            away["points"] += season.points_for_loss
        elif hs < aws:
            away["wins"] += 1
            home["losses"] += 1
            away["points"] += season.points_for_win
            home["points"] += season.points_for_loss
        else:
            home["draws"] += 1
            away["draws"] += 1
            home["points"] += season.points_for_draw
            away["points"] += season.points_for_draw
        match_rows.append((match.home_team_id, match.away_team_id, hs, aws))

    for row in rows.values():
        row["goal_difference"] = row["goals_for"] - row["goals_against"]

    # Resolve equal-points groups by mini-league points, then goals difference,
    # goals against, and clean sheets as described by the league rules.
    point_groups = defaultdict(list)
    for row in rows.values():
        point_groups[row["points"]].append(row)
    ordered = []
    for point_total in sorted(point_groups, reverse=True):
        group = point_groups[point_total]
        group_ids = {r["team"].pk for r in group}
        h2h = {pk: 0 for pk in group_ids}
        for home_id, away_id, hs, aws in match_rows:
            if home_id not in group_ids or away_id not in group_ids:
                continue
            if hs > aws:
                h2h[home_id] += season.points_for_win
                h2h[away_id] += season.points_for_loss
            elif hs < aws:
                h2h[away_id] += season.points_for_win
                h2h[home_id] += season.points_for_loss
            else:
                h2h[home_id] += season.points_for_draw
                h2h[away_id] += season.points_for_draw
        for row in group:
            row["head_to_head_points"] = h2h[row["team"].pk]
        descending = {"head_to_head", "goal_difference", "clean_sheets", "goals_for", "points"}
        allowed = {"head_to_head", "goal_difference", "goals_against", "clean_sheets", "goals_for"}

        def tie_break_key(row):
            values = []
            for rule in season.tie_breakers:
                if rule not in allowed:
                    continue
                value = row["head_to_head_points"] if rule == "head_to_head" else row[rule]
                values.append(-value if rule in descending else value)
            return (*values, row["team"].name.lower())

        ordered.extend(sorted(group, key=tie_break_key))
    return ordered


def get_leaderboard(season):
    if season is None:
        return []
    counted_matches = Q(
        match_appearances__match__season=season,
        match_appearances__match__score_approved_at__isnull=False,
        match_appearances__match__stage=Match.Stage.REGULAR,
    )
    players = Player.objects.filter(public_profile=True).annotate(
        games_played=Count("match_appearances__match", filter=counted_matches, distinct=True),
        goals=Count(
            "match_events",
            filter=Q(match_events__match__season=season,
                     match_events__match__score_approved_at__isnull=False,
                     match_events__match__stage=Match.Stage.REGULAR,
                     match_events__kind=MatchEvent.Kind.GOAL),
            distinct=True,
        ),
        assists=Count(
            "match_events",
            filter=Q(match_events__match__season=season,
                     match_events__match__score_approved_at__isnull=False,
                     match_events__match__stage=Match.Stage.REGULAR,
                     match_events__kind=MatchEvent.Kind.ASSIST),
            distinct=True,
        ),
        yellow_cards=Count(
            "match_events",
            filter=Q(match_events__match__season=season,
                     match_events__match__score_approved_at__isnull=False,
                     match_events__match__stage=Match.Stage.REGULAR,
                     match_events__kind=MatchEvent.Kind.YELLOW_CARD),
            distinct=True,
        ),
        red_cards=Count(
            "match_events",
            filter=Q(match_events__match__season=season,
                     match_events__match__score_approved_at__isnull=False,
                     match_events__match__stage=Match.Stage.REGULAR,
                     match_events__kind=MatchEvent.Kind.RED_CARD),
            distinct=True,
        ),
    ).prefetch_related("roster_memberships__season_team__team")
    leaderboard = []
    for player in players:
        membership = next(
            (m for m in player.roster_memberships.all() if m.season_team.season_id == season.id),
            None,
        )
        if not membership and not (player.goals or player.assists or player.games_played):
            continue
        points = player.goals * 2 + player.assists
        leaderboard.append({
            "player": player,
            "team": membership.season_team.name if membership else "—",
            "games_played": player.games_played,
            "points": points,
            "points_per_game": points / player.games_played if player.games_played else 0,
            "goals": player.goals,
            "assists": player.assists,
            "yellow_cards": player.yellow_cards,
            "red_cards": player.red_cards,
        })
    return sorted(
        leaderboard,
        key=lambda r: (-r["points"], -r["points_per_game"], -r["goals"], r["player"].display_name.lower()),
    )


def section(request, slug):
    try:
        title, heading, description = SECTIONS[slug]
    except KeyError as exc:
        raise Http404 from exc
    seasons = Season.objects.filter(is_published=True).order_by("-year", "-start_date")
    season = get_selected_season(request)
    if request.GET.get("season") and season is None:
        raise Http404("Season not found")
    context = {
        "active_slug": slug,
        "title": title,
        "heading": heading,
        "description": description,
        "sections": {k: v for k, v in SECTIONS.items() if k not in {"awards", "gallery"}},
        "season": season,
        "seasons": seasons,
    }
    if slug == "teams" and season:
        season_teams = SeasonTeam.objects.filter(season=season).select_related("team").prefetch_related(
            "roster__player"
        )
        context["season_teams"] = season_teams
        context["selected_team"] = request.GET.get("team", "")
        context["team_options"] = season_teams
        if context["selected_team"]:
            season_teams = season_teams.filter(team__slug=context["selected_team"])
        context["display_teams"] = [
            {"entry": entry, "legacy_badge_url": LEGACY_TEAM_BADGES.get(entry.team.slug)}
            for entry in season_teams
        ]
    elif slug == "schedule" and season:
        context["matches"] = Match.objects.filter(season=season).select_related(
            "home_team__team", "away_team__team"
        )
    elif slug == "standings" and season:
        context["standings"] = get_standings(season)
        context["leaderboard"] = get_leaderboard(season)
    elif slug == "rules" and season:
        context["rules"] = SeasonRules.objects.filter(season=season).first()
    elif slug == "awards":
        awards = Award.objects.select_related("season", "player", "season_team__team").filter(
            season__is_published=True
        )
        if season:
            awards = awards.filter(season=season)
        context["awards"] = awards
    elif slug == "gallery":
        gallery = GalleryItem.objects.filter(is_published=True)
        if season:
            gallery = gallery.filter(Q(season=season) | Q(season__isnull=True))
        context["gallery_items"] = gallery.select_related("season")
    return render(request, "siteapp/section.html", context)
