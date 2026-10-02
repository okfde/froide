from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

import pytest
from playwright.async_api import Page, expect

from froide.foirequest.tests.factories import FoiAttachmentFactory

from .utils import do_login

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
