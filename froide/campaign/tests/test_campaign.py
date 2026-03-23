from django.contrib.auth import get_user_model
from django.urls import reverse

import pytest
from playwright.async_api import Page, expect

from froide.campaign.models import Campaign
from froide.foirequest.models import FoiRequest
from froide.publicbody.factories import PublicBodyFactory
from froide.publicbody.models import PublicBody
from froide.tests.live.utils import do_login, go_to_make_request_url

User = get_user_model()


@pytest.mark.django_db
def test_campaign_request_match(world, client):
    ok = client.login(email="info@fragdenstaat.de", password="froide")
    assert ok

    campaign = Campaign(
        name="test",
        slug="test",
        ident="test",
        request_match="needle\nnoodle",
        request_hint="forbidden word!",
        active=True,
        public=True,
    )
    campaign.save()

    pb = PublicBodyFactory()
    post = {
        "subject": "Test-Subject needle",
        "body": "This is a test no-dle",
        "publicbody": pb.pk,
        "public": False,
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 302

    req = FoiRequest.objects.order_by("pk").last()
    assert req
    assert req.title == post["subject"]
    assert req.status == "awaiting_response"

    request_count = FoiRequest.objects.count()

    pb = PublicBodyFactory()
    post = {
        "subject": "Test-Subject needle",
        "body": "This is a test noodle",
        "publicbody": pb.pk,
        "public": False,
    }
    response = client.post(reverse("foirequest-make_request"), post)
    assert response.status_code == 400
    assert campaign.request_hint in str(response.content)
    assert FoiRequest.objects.count() == request_count


@pytest.mark.django_db
@pytest.mark.asyncio(loop_scope="session")
async def test_campaign_request_match_live(
    page: Page, live_server, public_body_with_index, dummy_user
):
    campaign = Campaign(
        name="test",
        slug="test",
        ident="test",
        request_match="needle",
        request_hint="forbidden word!",
        active=True,
        public=True,
    )
    campaign.save()

    req_title = "FoiRequest Number"
    req_body = "Documents needle"

    await do_login(page, live_server)
    await go_to_make_request_url(page, live_server)

    await page.get_by_role("button", name="Make request").click()
    await page.locator("#step_find_similar").get_by_role("button", name="Skip").click()

    pb = PublicBody.objects.first()
    await page.locator(".search-public_bodies").fill(pb.name)
    await page.locator(".search-public_bodies-submit").click()
    buttons = page.locator(".search-results .search-result .btn")
    await expect(buttons).to_have_count(1)
    await page.locator(".search-results .search-result .btn >> nth=0").click()

    await page.fill("[name=subject]", req_title)
    await page.fill("[name=body]", req_body)
    await page.locator("[name=confirm]").click()
    await page.locator("#step_write_request .btn-primary").click()

    await page.locator("#step_request_public .btn-primary").click()

    await page.locator("#send-request-button").click()

    await expect(page.locator("#make-request")).to_contain_text(campaign.request_hint)
