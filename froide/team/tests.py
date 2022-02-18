from django.test import TestCase
from django.urls import reverse

import factory

from froide.account.factories import UserFactory
from froide.foirequest.tests import factories

from .models import Team, TeamMembership
from .services import TeamService


class TeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Team

    name = factory.Sequence(lambda n: "Team {}".format(n))


class TeamMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TeamMembership

    user = factory.SubFactory(UserFactory)
    team = factory.SubFactory(TeamFactory)
    role = TeamMembership.ROLE.VIEWER
    status = TeamMembership.MEMBERSHIP_STATUS.ACTIVE


class TeamTest(TestCase):
    def setUp(self):
        factories.make_world()
        self.user = UserFactory.create()

        self.owner_team = TeamFactory.create()
        TeamMembershipFactory.create(
            user=self.user, team=self.owner_team, role=TeamMembership.ROLE.OWNER
        )
        TeamMembershipFactory.create(
            team=self.owner_team, role=TeamMembership.ROLE.OWNER
        )

        self.editor_team = TeamFactory.create()
        TeamMembershipFactory.create(
            user=self.user, team=self.editor_team, role=TeamMembership.ROLE.EDITOR
        )
        TeamMembershipFactory.create(
            team=self.editor_team, role=TeamMembership.ROLE.OWNER
        )
        self.other_team = TeamFactory.create()
        TeamMembershipFactory.create(
            team=self.other_team, role=TeamMembership.ROLE.EDITOR
        )
        TeamMembershipFactory.create(
            team=self.other_team, role=TeamMembership.ROLE.OWNER
        )

    def test_owner_teams(self):
        self.assertEqual(Team.objects.get_owner_teams(self.user).count(), 1)

    def test_editor_owner_teams(self):
        self.assertEqual(Team.objects.get_editor_owner_teams(self.user).count(), 2)

    def test_already_exists(self):
        invite = TeamMembershipFactory.create(
            user=None,
            team=self.owner_team,
            role=TeamMembership.ROLE.OWNER,
            status=TeamMembership.MEMBERSHIP_STATUS.INVITED,
            email=self.user.email,
        )
        team_service = TeamService(invite)
        secret = team_service.generate_invite_secret()
        loggedin = self.client.login(email=self.user.email, password="froide")
        self.assertTrue(loggedin)

        url = reverse(
            "team-join",
            kwargs={"pk": invite.pk, "secret": secret + "a"},  # Broken secret
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        url = reverse("team-join", kwargs={"pk": invite.pk, "secret": secret})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        user_member_count = TeamMembership.objects.filter(
            user=self.user, team=self.owner_team
        ).count()
        self.assertEqual(user_member_count, 1)
