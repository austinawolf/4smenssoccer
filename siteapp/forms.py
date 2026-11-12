from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import RosterMembership


class StaffAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class ScoreForm(forms.Form):
    home_score = forms.IntegerField(min_value=0, max_value=99, label="Home team")
    away_score = forms.IntegerField(min_value=0, max_value=99, label="Away team")


class ScoreSubmissionForm(ScoreForm):
    def __init__(self, *args, team=None, match=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.match = match
        self.player_rows = []
        if team is None:
            return
        roster = RosterMembership.objects.filter(season_team=team).exclude(
            status=RosterMembership.Status.INACTIVE
        ).select_related("player")
        for membership in roster:
            player = membership.player
            goals_name = f"goals_{player.pk}"
            assists_name = f"assists_{player.pk}"
            self.fields[goals_name] = forms.IntegerField(
                min_value=0, max_value=99, required=False, initial=0, label=f"{player.display_name} goals"
            )
            self.fields[assists_name] = forms.IntegerField(
                min_value=0, max_value=99, required=False, initial=0, label=f"{player.display_name} assists"
            )
            self.player_rows.append({
                "player": player,
                "goals_name": goals_name,
                "assists_name": assists_name,
            })

    def get_player_stats(self):
        stats = []
        for row in self.player_rows:
            goals = self.cleaned_data.get(row["goals_name"]) or 0
            assists = self.cleaned_data.get(row["assists_name"]) or 0
            if goals or assists:
                stats.append({"player": row["player"], "goals": goals, "assists": assists})
        return stats

    def clean(self):
        cleaned_data = super().clean()
        if self.team and self.match and "home_score" in cleaned_data and "away_score" in cleaned_data:
            reported_goals = sum(
                cleaned_data.get(f"goals_{row['player'].pk}") or 0
                for row in self.player_rows
            )
            team_score = (
                cleaned_data["home_score"]
                if self.team.pk == self.match.home_team_id
                else cleaned_data["away_score"]
            )
            if reported_goals > team_score:
                raise forms.ValidationError("Player goals cannot exceed the score reported for your team.")
        return cleaned_data


class ReviewDecisionForm(forms.Form):
    action = forms.ChoiceField(choices=(("approve", "Approve result"), ("reject", "Reject and request correction")))
    home_score = forms.IntegerField(min_value=0, max_value=99, label="Official home score")
    away_score = forms.IntegerField(min_value=0, max_value=99, label="Official away score")
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}), label="Decision note")


class PlayerPhotoForm(forms.Form):
    photo = forms.ImageField(widget=forms.ClearableFileInput(attrs={"accept": "image/*", "capture": "environment"}))

    def clean_photo(self):
        photo = self.cleaned_data["photo"]
        if photo.size > 8 * 1024 * 1024:
            raise forms.ValidationError("Choose an image smaller than 8 MB.")
        return photo
