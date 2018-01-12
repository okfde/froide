# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django import template

from ..models import Team

register = template.Library()


@register.filter(name='can_use_teams')
def can_use_teams(user):
    in_team = Team.objects.get_for_user(user).exists()
    return in_team or user.has_perm('team.can_use_teams')
