from django.dispatch import Signal

team_changed = Signal()  # providing_args=["team", "old_team"]
