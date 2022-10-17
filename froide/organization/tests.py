from django.contrib.auth import get_user_model
from django.urls import reverse
from django.views.generic.list import MultipleObjectMixin

import factory
import pytest
from pytest_factoryboy import register

from froide.account.factories import UserFactory

from .models import Organization, OrganizationMembership
from .services import OrganizationService
from .views import OrganizationDetailView, OrganizationListView

User = get_user_model()


@register
class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization

    name = factory.Sequence(lambda n: "Organization {}".format(n))
    slug = factory.Sequence(lambda n: "organization-{}".format(n))
    description = factory.Faker("text")
    show_in_list = False


@register
class OrganizationMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrganizationMembership

    user = factory.SubFactory(UserFactory)
    organization = factory.SubFactory(OrganizationFactory)
    role = OrganizationMembership.ROLE.MEMBER
    status = OrganizationMembership.STATUS.ACTIVE


register(OrganizationFactory, "public_orga", show_in_list=True)
register(OrganizationFactory, "private_orga", show_in_list=False)
register(
    OrganizationMembershipFactory,
    "private_orga",
)
register(UserFactory, "user")


@pytest.mark.django_db
@pytest.mark.parametrize("view", [OrganizationListView, OrganizationDetailView])
def test_organization_show_in_list_orga_view(
    world,
    public_orga: Organization,
    private_orga: Organization,
    view: MultipleObjectMixin,
):
    qs = view().get_queryset()
    assert public_orga in qs
    assert private_orga not in qs


@pytest.mark.django_db
def test_organizations_invite(user, client, organization: Organization):
    # Invite user
    beginning_member_count = organization.member_count
    invite = OrganizationMembershipFactory.create(
        user=None,
        organization=organization,
        role=OrganizationMembership.ROLE.OWNER,
        status=OrganizationMembership.STATUS.INVITED,
        email=user.email,
    )
    organization_service = OrganizationService(invite)
    secret = organization_service.generate_invite_secret()

    assert organization.member_count == beginning_member_count

    loggedin = client.login(email=user.email, password="froide")
    assert loggedin is True

    url = reverse(
        "organization-join",
        kwargs={
            "slug": organization.slug,
            "pk": invite.pk,
            "secret": secret + "a",
        },  # Broken secret
    )
    response = client.get(url)
    assert response.status_code == 404

    url = reverse(
        "organization-join",
        kwargs={"slug": organization.slug, "pk": invite.pk, "secret": secret},
    )
    response = client.get(url)

    # After clicking the join link, the user is asked to confirm joining again.
    # The user is not added to the organization automatically
    assert response.status_code == 200
    assert organization.member_count == beginning_member_count

    response = client.post(url)
    assert response.status_code == 302

    user_member_count = OrganizationMembership.objects.filter(
        user=user, organization=organization
    ).count()

    # After submitting the invite form, the user is added to the member list
    assert user_member_count == 1
    assert organization.member_count == beginning_member_count + 1


@pytest.mark.django_db
def test_organization_user_list_display(
    organization_membership: OrganizationMembership, client
):
    user: User = organization_membership.user
    organization = organization_membership.organization

    url = reverse(
        "organization-detail",
        kwargs={"slug": organization.slug},
    )

    user.private = False
    user.save()

    response = client.get(url)
    assert response.status_code == 200
    assert user.get_full_name() in response.content.decode()

    user.private = True
    user.save()

    response = client.get(url)
    assert response.status_code == 200
    assert user.get_full_name() not in response.content.decode()
