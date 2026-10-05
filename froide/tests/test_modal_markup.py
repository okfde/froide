from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone

import pytest
from bs4 import BeautifulSoup, Tag

from froide.foirequest.models import DeliveryStatus
from froide.team.models import TeamMembership
from froide.team.tests import TeamMembershipFactory


def has_accessible_name(modal: Tag):
    title_id = modal.get("aria-labelledby")
    assert title_id, f"{modal['id']} has no aria-labelledby"
    title = modal.find(id=title_id)
    assert title is not None, f"{modal['id']} is labelled by a missing element"
    assert title.get_text(strip=True), f"{modal['id']} is labelled by an empty element"


def title_is_h1(modal: Tag):
    title = modal.select_one(".modal-title")
    assert title is not None, f"{modal['id']} has no title"
    assert title.name == "h1", f"{modal['id']} has a <{title.name}> as title"


def is_focusable(modal: Tag):
    # Without it, Bootstrap cannot move the focus into the modal when it opens
    assert modal.get("tabindex") == "-1", f"{modal['id']} has no tabindex=-1"


def has_one_close_button(modal: Tag):
    buttons = modal.select("button.btn-close[aria-label]")
    assert len(buttons) == 1, f"{modal['id']} has {len(buttons)} close buttons"


RULES = [
    has_accessible_name,
    title_is_h1,
    is_focusable,
    has_one_close_button,
]


def get_modals(client, url: str, expected: list[str]) -> list[Tag]:
    """The modals of a page, which has to contain one for each expected id prefix."""
    response = client.get(url)
    assert response.status_code == 200
    soup = BeautifulSoup(response.content.decode(), "lxml")
    modals = soup.select(".modal")

    ids = [modal.get("id", "") for modal in modals]
    for prefix in expected:
        assert any(id.startswith(prefix) for id in ids), f"No {prefix} modal in {ids}"
    return modals


def make_request(foi_request_factory, foi_message_factory, **message_kwargs):
    req = foi_request_factory(created_at=timezone.now())
    message = foi_message_factory(
        request=req, is_response=False, sender_user=req.user, **message_kwargs
    )
    return req, message


@pytest.fixture
def requester_page(client, foi_request_factory, foi_message_factory):
    # Only messages of a manual kind can be edited
    req, _ = make_request(foi_request_factory, foi_message_factory, kind="post")
    client.force_login(req.user)
    return get_modals(
        client,
        req.get_absolute_url(),
        ["description-redact-", "message-edit-", "message-redact-", "problemreport-"],
    )


@pytest.fixture
def moderator_page(client, user_factory, foi_request_factory, foi_message_factory):
    # Moderators can resend a message that could not be delivered
    req, message = make_request(foi_request_factory, foi_message_factory)
    DeliveryStatus.objects.create(
        message=message, status=DeliveryStatus.Delivery.STATUS_FAILED
    )
    moderator = user_factory()
    moderator.user_permissions.add(
        Permission.objects.get(
            codename="moderate", content_type__app_label="foirequest"
        )
    )
    client.force_login(moderator)
    return get_modals(client, req.get_absolute_url(), ["resend-"])


@pytest.fixture
def anonymous_page(client, foi_request_factory, foi_message_factory):
    req, _ = make_request(foi_request_factory, foi_message_factory)
    return get_modals(
        client,
        req.get_absolute_url(),
        ["follow-form-", "share-mastodon-", "problemreport-"],
    )


@pytest.fixture
def withdrawn_page(client, foi_request_factory, foi_message_factory):
    req, _ = make_request(foi_request_factory, foi_message_factory)
    client.force_login(req.user)
    # Set by the view that withdraws the request
    session = client.session
    session["show_withdrawal_popup"] = req.id
    session.save()
    return get_modals(client, req.get_absolute_url(), ["withdrawalModal"])


@pytest.fixture
def search_page(client):
    return get_modals(client, reverse("foirequest-list"), ["searchalert-form-modal"])


@pytest.fixture
def team_page(client, user):
    membership = TeamMembershipFactory(user=user, role=TeamMembership.ROLE.OWNER)
    client.force_login(user)
    return get_modals(
        client,
        reverse("team-detail", kwargs={"pk": membership.team.pk}),
        ["delete-team-modal"],
    )


PAGES = [
    "requester_page",
    "moderator_page",
    "anonymous_page",
    "withdrawn_page",
    "search_page",
    "team_page",
]


@pytest.mark.django_db
@pytest.mark.parametrize("page", PAGES)
def test_modal_markup(request, page):
    modals = request.getfixturevalue(page)

    for rule in RULES:
        for modal in modals:
            rule(modal)
