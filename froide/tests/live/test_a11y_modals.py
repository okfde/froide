import re

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

import pytest
from playwright.async_api import Page, expect

from froide.foirequest.tests.factories import FoiAttachmentFactory

from .utils import do_login, go_to_request_page

ATTACHMENT_NAME = "letter.pdf"


@pytest.fixture
def foirequest(dummy_user, foi_request_factory, foi_message_factory):
    req = foi_request_factory(
        user=dummy_user, created_at=timezone.now(), status="resolved"
    )
    foi_message_factory(request=req, is_response=False, sender_user=dummy_user)
    return req


@pytest.fixture
def attachment(foirequest, foi_message_factory):
    message = foi_message_factory(request=foirequest)
    return FoiAttachmentFactory(belongs_to=message, name=ATTACHMENT_NAME, approved=True)


@pytest.mark.django_db
@pytest.mark.xdist_group(name="sequential")
@pytest.mark.asyncio(loop_scope="session")
@override_settings(SERVE_MEDIA=True)
async def test_bs_modal(page: Page, live_server, attachment):
    """The modal component that Vue renders, here as the attachment preview."""
    message = attachment.belongs_to
    await do_login(page, live_server)
    path = reverse(
        "foirequest-manage_attachments",
        kwargs={"slug": message.request.slug, "message_id": message.id},
    )
    await page.goto(live_server.url + path)

    trigger = page.locator(".icon-with-name a")
    await trigger.click()

    dialog = page.get_by_role("dialog", name=ATTACHMENT_NAME)
    await expect(dialog).to_be_visible()
    await expect(dialog.get_by_role("heading", level=1)).to_have_text(ATTACHMENT_NAME)
    await expect(dialog.get_by_role("button", name="Close")).to_have_count(1)

    await page.keyboard.press("Escape")

    await expect(dialog).to_be_hidden()
    await expect(trigger).to_be_focused()


@pytest.mark.django_db
@pytest.mark.xdist_group(name="sequential")
@pytest.mark.asyncio(loop_scope="session")
async def test_withdrawal_modal_send_message_moves_focus_to_message(
    page: Page, live_server, foirequest
):
    await do_login(page, live_server)
    await go_to_request_page(page, live_server, foirequest)

    # Withdrawing the request opens the modal
    await page.locator(".info-box__edit-button").click()
    await page.locator('select[name="resolution"]').select_option("user_withdrew")
    await page.locator("#set-status-submit").click()
    dialog = page.locator("#withdrawalModal")
    await expect(dialog).to_be_visible()

    await dialog.get_by_role("button", name="Send message").click()

    await expect(dialog).to_be_hidden()
    await expect(page.locator('[name="sendmessage-message"]')).to_be_focused()


@pytest.mark.django_db
@pytest.mark.xdist_group(name="sequential")
@pytest.mark.asyncio(loop_scope="session")
async def test_share_mastodon_modal_stays_open_on_invalid_input(
    page: Page, live_server, foirequest
):
    await go_to_request_page(page, live_server, foirequest)

    await page.locator('[data-bs-target^="#share-mastodon-"]').click()
    dialog = page.locator('.modal[id^="share-mastodon-"]')
    await expect(dialog).to_be_visible()

    # The instance field is required and still empty
    await dialog.locator('button[type="submit"]').click()

    # Bootstrap drops the class as soon as it starts to hide the modal
    await expect(dialog).to_have_class(re.compile(r"\bshow\b"))
    await expect(dialog.locator("input:invalid")).to_be_visible()
