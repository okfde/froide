from django.test import TestCase
from django.urls import reverse

import factory

from froide.foirequest.tests import factories

from .models import Team, TeamMembership
from .services import TeamService


class TeamFactory(factory.DjangoModelFactory):
    class Meta:
        model = Team

    name = factory.Sequence(lambda n: 'Team {}'.format(n))


class TeamMembershipFactory(factory.DjangoModelFactory):
    class Meta:
        model = TeamMembership

    user = factory.SubFactory(factories.UserFactory)
    team = factory.SubFactory(TeamFactory)
    role = TeamMembership.ROLE_VIEWER
    status = TeamMembership.MEMBERSHIP_STATUS_ACTIVE


class TeamTest(TestCase):
    def setUp(self):
        factories.make_world()
        self.user = factories.UserFactory.create()

        self.owner_team = TeamFactory.create()
        TeamMembershipFactory.create(
            user=self.user,
            team=self.owner_team,
            role=TeamMembership.ROLE_OWNER
        )
        TeamMembershipFactory.create(
            team=self.owner_team,
            role=TeamMembership.ROLE_OWNER
        )

        self.editor_team = TeamFactory.create()
        TeamMembershipFactory.create(
            user=self.user,
            team=self.editor_team,
            role=TeamMembership.ROLE_EDITOR
        )
        TeamMembershipFactory.create(
            team=self.editor_team,
            role=TeamMembership.ROLE_OWNER
        )
        self.other_team = TeamFactory.create()
        TeamMembershipFactory.create(
            team=self.other_team,
            role=TeamMembership.ROLE_EDITOR
        )
        TeamMembershipFactory.create(
            team=self.other_team,
            role=TeamMembership.ROLE_OWNER
        )

    def test_owner_teams(self):
        self.assertEqual(
            Team.objects.get_owner_teams(self.user).count(), 1
        )

    def test_editor_owner_teams(self):
        self.assertEqual(
            Team.objects.get_editor_owner_teams(self.user).count(), 2
        )

    def test_already_exists(self):
        invite = TeamMembershipFactory.create(
            user=None,
            team=self.owner_team,
            role=TeamMembership.ROLE_OWNER,
            status=TeamMembership.MEMBERSHIP_STATUS_INVITED,
            email=self.user.email
        )
        team_service = TeamService(invite)
        secret = team_service.generate_invite_secret()
        loggedin = self.client.login(email=self.user.email, password='froide')
        self.assertTrue(loggedin)

        url = reverse('team-join', kwargs={
            'pk': invite.pk,
            'secret': secret + 'a'  # Broken secret
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        url = reverse('team-join', kwargs={
            'pk': invite.pk,
            'secret': secret
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        user_member_count = TeamMembership.objects.filter(
            user=self.user,
            team=self.owner_team
        ).count()
        self.assertEqual(user_member_count, 1)
