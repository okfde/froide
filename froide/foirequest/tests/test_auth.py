from datetime import timedelta

from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.utils import timezone

import pytest
from oauth2_provider.models import get_access_token_model, get_application_model

from froide.account.factories import UserFactory
from froide.campaign.models import Campaign
from froide.foirequest.auth import (
    get_read_foirequest_queryset,
    get_write_foirequest_queryset,
)
from froide.team.models import TeamMembership
from froide.team.tests import TeamMembershipFactory

from ..models import FoiRequest
from .factories import FoiRequestFactory

Application = get_application_model()
AccessToken = get_access_token_model()


@pytest.fixture
def user():
    return UserFactory.create()


@pytest.fixture
def other_user():
    return UserFactory.create()


@pytest.fixture
def staff_user():
    return UserFactory.create(is_staff=True)


@pytest.fixture
def view_permission():
    ct = ContentType.objects.get_for_model(FoiRequest)
    return Permission.objects.get(
        codename="view_foirequest",
        content_type=ct,
    )


@pytest.fixture
def change_permission():
    ct = ContentType.objects.get_for_model(FoiRequest)
    return Permission.objects.get(
        codename="change_foirequest",
        content_type=ct,
    )


@pytest.fixture
def staff_user_read(view_permission):
    user = UserFactory.create(is_staff=True)
    user.user_permissions.add(view_permission)
    return user


@pytest.fixture
def staff_user_write(change_permission):
    user = UserFactory.create(is_staff=True)
    user.user_permissions.add(change_permission)
    return user


@pytest.fixture
def team_member():
    return TeamMembershipFactory.create()


@pytest.fixture
def team_member_write(team_member):
    return TeamMembershipFactory.create(
        team=team_member.team, role=TeamMembership.ROLE.EDITOR
    )


@pytest.fixture
def oauth_app(other_user):
    return Application.objects.create(
        name="Test Application",
        redirect_uris="http://localhost http://example.com http://example.org",
        user=other_user,
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
    )


@pytest.fixture
def read_token():
    return AccessToken(
        scope="read:request",
        expires=timezone.now() + timedelta(seconds=300),
    )


@pytest.fixture
def write_token():
    return AccessToken(
        scope="write:request",
        expires=timezone.now() + timedelta(seconds=300),
    )


@pytest.fixture
def bad_token():
    return AccessToken(
        scope="read:profile",
        expires=timezone.now() + timedelta(seconds=300),
    )


@pytest.fixture
def campaign():
    group = Group.objects.create(name="Campaign")
    return Campaign.objects.create(name="Test Campaign", group=group)


@pytest.fixture
def campaign_user(campaign):
    user = UserFactory.create(is_staff=True)
    user.groups.add(campaign.group)
    return user


@pytest.fixture
def foirequest(user, team_member):
    return FoiRequestFactory.create(
        user=user,
        visibility=FoiRequest.VISIBILITY.VISIBLE_TO_PUBLIC,
        team=team_member.team,
    )


@pytest.fixture
def foirequest_campaign(campaign):
    return FoiRequestFactory.create(
        campaign=campaign,
        visibility=FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER,
    )


@pytest.fixture
def foirequest_unpublished(user, team_member):
    return FoiRequestFactory.create(
        user=user,
        visibility=FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER,
        team=team_member.team,
    )


@pytest.mark.django_db
def test_read_foirequest_queryset_user(
    user,
    foirequest_unpublished,
    team_member,
    other_user,
    read_token,
    bad_token,
    staff_user,
    staff_user_read,
):
    # Anon request no access
    anon_req = HttpRequest()
    anon_req.user = AnonymousUser()
    assert get_read_foirequest_queryset(anon_req).count() == 0

    other_user_req = HttpRequest()
    other_user_req.user = other_user
    assert get_read_foirequest_queryset(other_user_req).count() == 0

    user_req = HttpRequest()
    user_req.user = user
    assert get_read_foirequest_queryset(user_req).get() == foirequest_unpublished

    team_member_req = HttpRequest()
    team_member_req.user = team_member.user
    assert get_read_foirequest_queryset(team_member_req).get() == foirequest_unpublished

    user_req = HttpRequest()
    user_req.user = staff_user
    assert get_read_foirequest_queryset(user_req).count() == 0

    user_req = HttpRequest()
    user_req.user = staff_user_read
    assert get_read_foirequest_queryset(user_req).get() == foirequest_unpublished

    token_req = HttpRequest()
    token_req.user = user
    token_req.auth = bad_token
    assert get_read_foirequest_queryset(token_req).count() == 0

    token_req = HttpRequest()
    token_req.user = user
    token_req.auth = read_token
    assert get_read_foirequest_queryset(token_req).get() == foirequest_unpublished


@pytest.mark.django_db
def test_write_foirequest_queryset_user(
    user,
    foirequest,
    team_member,
    team_member_write,
    other_user,
    staff_user_read,
    staff_user_write,
    read_token,
    write_token,
):
    anon_req = HttpRequest()
    anon_req.user = AnonymousUser()
    assert get_write_foirequest_queryset(anon_req).count() == 0

    other_user_req = HttpRequest()
    other_user_req.user = other_user
    assert get_write_foirequest_queryset(other_user_req).count() == 0

    user_req = HttpRequest()
    user_req.user = user
    assert get_write_foirequest_queryset(user_req).get() == foirequest

    team_member_req = HttpRequest()
    team_member_req.user = team_member.user
    assert get_write_foirequest_queryset(team_member_req).count() == 0

    team_member_req = HttpRequest()
    team_member_req.user = team_member_write.user
    assert get_write_foirequest_queryset(team_member_req).get() == foirequest

    user_req = HttpRequest()
    user_req.user = staff_user_read
    assert get_write_foirequest_queryset(user_req).count() == 0

    user_req = HttpRequest()
    user_req.user = staff_user_write
    assert get_write_foirequest_queryset(user_req).get() == foirequest

    token_req = HttpRequest()
    token_req.user = user
    token_req.auth = read_token
    assert get_write_foirequest_queryset(token_req).count() == 0

    token_req = HttpRequest()
    token_req.user = user
    token_req.auth = write_token
    assert get_write_foirequest_queryset(token_req).get() == foirequest


@pytest.mark.django_db
def test_campaign_access(foirequest_campaign, other_user, campaign_user):
    anon_req = HttpRequest()
    anon_req.user = AnonymousUser()
    assert get_write_foirequest_queryset(anon_req).count() == 0

    other_user_req = HttpRequest()
    other_user_req.user = other_user
    assert get_write_foirequest_queryset(other_user_req).count() == 0

    req = HttpRequest()
    req.user = campaign_user
    assert get_write_foirequest_queryset(req).get() == foirequest_campaign
