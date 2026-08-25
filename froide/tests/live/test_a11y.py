from django.urls import reverse

import pytest
from playwright.async_api import Page, expect

from .utils import do_login

# (url name, reverse kwargs)
PAGES = [
    ("index", {}),
    ("account-login", {}),
    ("account-signup", {}),
    ("foirequest-make_request", {}),
]

# Pages that redirect anonymous visitors to the login page
LOGGED_IN_PAGES = [
    ("account-settings", {}),
    ("account-confirmed", {}),
    ("publicbody-propose", {}),
]

# Pages that are only shown to staff users
STAFF_PAGES = [
    ("document-upload", {}),
]


async def _check_page(page: Page, live_server, check_a11y, url_name: str, kwargs: dict):
    response = await page.goto(live_server.url + reverse(url_name, kwargs=kwargs))
    assert response is not None
    assert response.status == 200, f"{url_name} returned HTTP {response.status}"

    await check_a11y(page)


@pytest.mark.django_db
@pytest.mark.xdist_group(name="sequential")
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("url_name,kwargs", PAGES, ids=[entry[0] for entry in PAGES])
async def test_a11y(page: Page, live_server, check_a11y, url_name: str, kwargs: dict):
    await _check_page(page, live_server, check_a11y, url_name, kwargs)


@pytest.mark.django_db
@pytest.mark.xdist_group(name="sequential")
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "url_name,kwargs", LOGGED_IN_PAGES, ids=[entry[0] for entry in LOGGED_IN_PAGES]
)
async def test_a11y_logged_in(
    page: Page, live_server, check_a11y, dummy_user, url_name: str, kwargs: dict
):
    await do_login(page, live_server)
    await _check_page(page, live_server, check_a11y, url_name, kwargs)


@pytest.mark.django_db
@pytest.mark.xdist_group(name="sequential")
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "url_name,kwargs", STAFF_PAGES, ids=[entry[0] for entry in STAFF_PAGES]
)
async def test_a11y_staff(
    page: Page, live_server, check_a11y, dummy_staff_user, url_name: str, kwargs: dict
):
    await do_login(page, live_server, username=dummy_staff_user.username)
    await _check_page(page, live_server, check_a11y, url_name, kwargs)


@pytest.mark.django_db
@pytest.mark.xdist_group(name="sequential")
@pytest.mark.asyncio(loop_scope="session")
async def test_a11y_foirequest_list_search_options(page: Page, live_server, check_a11y):
    """FOI request list with opened additional search options"""

    await page.goto(live_server.url + reverse("foirequest-list"))

    await page.locator("details > summary").click()
    await expect(page.locator("details[open]")).to_have_count(1)

    await check_a11y(page)
