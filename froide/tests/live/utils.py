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
async def go_to_create_account_step(page, live_server, pb):
    """Write a request to `pb` while logged out, up to the sign up step."""
    await go_to_make_request_url(page, live_server, pb=pb)
    await page.fill("[name=subject]", "FoiRequest Number")
    await page.fill("[name=body]", "Documents describing & something...")
    await page.locator("[name=confirm]").click()
    await page.locator("#step_write_request .btn-primary").click()
    await page.locator("#step_request_public .btn-primary").click()
    await page.locator("#step_login_create .btn-primary >> nth=0").click()


@pytest.mark.asyncio(loop_scope="session")
async def fill_create_account_step(page, email="peter.parker@example.com"):
    await page.fill("[name=first_name]", "Peter")
    await page.fill("[name=last_name]", "Parker")
    await page.fill("[name=address]", "123 Queens Blvd\n12345 Queens")
    await page.fill("[name=user_email]", email)
    await page.locator("[name=terms]").click()


@pytest.mark.asyncio(loop_scope="session")
async def go_to_request_page(page, live_server, foirequest):
    path = reverse("foirequest-show", kwargs={"slug": foirequest.slug})
    await page.goto(live_server.url + path)


@pytest.mark.asyncio(loop_scope="session")
async def do_login(page, live_server, username="dummy"):
    await page.goto(live_server.url + reverse("account-login"))
    user = User.objects.get(username=username)
    await page.fill("[name=username]", user.email)
    await page.fill("[name=password]", "froide")
    await page.locator('button.btn.btn-primary[type="submit"]').click()
    await expect(page.locator("#navbaraccount-link")).to_have_count(1)
