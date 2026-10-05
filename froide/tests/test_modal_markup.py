from django.utils import timezone

import pytest
from bs4 import BeautifulSoup, Tag


def has_one_close_button(modal: Tag):
    buttons = modal.select("button.btn-close[aria-label]")
    assert len(buttons) == 1, f"{modal['id']} has {len(buttons)} close buttons"


RULES = [
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


PAGES = [
    "requester_page",
]


@pytest.mark.django_db
@pytest.mark.parametrize("page", PAGES)
def test_modal_markup(request, page):
    modals = request.getfixturevalue(page)

    for rule in RULES:
        for modal in modals:
            rule(modal)
