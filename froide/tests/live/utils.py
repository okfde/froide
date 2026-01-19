from django.contrib.auth import get_user_model
from django.urls import reverse

import pytest
from playwright.async_api import expect

User = get_user_model()


@pytest.mark.asyncio(loop_scope="session")
async def go_to_make_request_url(page, live_server, pb=None):
    if pb is None:
        path = reverse("foirequest-make_request")
    else:
        path = reverse(
            "foirequest-make_request",
            kwargs={"publicbody_slug": pb.slug},
        )
    url = live_server.url + path
    await page.goto(url=url)


@pytest.mark.asyncio(loop_scope="session")
async def go_to_request_page(page, live_server, foirequest):
    path = reverse("foirequest-show", kwargs={"slug": foirequest.slug})
    await page.goto(live_server.url + path)


@pytest.mark.asyncio(loop_scope="session")
async def do_login(page, live_server, navigate=True):
    if navigate:
        await page.goto(live_server.url + reverse("account-login"))
        user = User.objects.get(username="dummy")
        await page.fill("[name=username]", user.email)
        await page.fill("[name=password]", "froide")
        await page.locator('button.btn.btn-primary[type="submit"]').click()
        await expect(page.locator("#navbaraccount-link")).to_have_count(1)
