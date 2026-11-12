from django.http import Http404
from django.shortcuts import render

SECTIONS = {
    "home": ("Home", "4S Ranch Men's Soccer League", "League information and season updates will live here."),
    "teams": ("Teams", "Teams", "Browse teams and season rosters."),
    "schedule": ("Schedule", "Schedule", "View upcoming games and approved results."),
    "standings": ("Standings", "Standings", "Follow the season table and player leaderboard."),
    "coaches": ("Coaches", "Coaches", "Privileged coaches will sign in here to report match scores."),
    "admin": ("Admin", "Admin", "League administrators will review reported scores here."),
    "rules": ("Rules", "Rules", "Read the current league rules."),
}


def section(request, slug):
    try:
        title, heading, description = SECTIONS[slug]
    except KeyError as exc:
        raise Http404 from exc
    return render(request, "siteapp/section.html", {
        "active_slug": slug,
        "title": title,
        "heading": heading,
        "description": description,
        "sections": SECTIONS,
    })
