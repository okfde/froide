from django.urls import reverse

import pytest
from playwright.async_api import Page

# (url name, reverse kwargs)
PAGES = [
    ("index", {}),
    ("account-login", {}),
    ("account-signup", {}),
    ("foirequest-make_request", {}),
]


@pytest.mark.django_db
@pytest.mark.xdist_group(name="sequential")
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("url_name,kwargs", PAGES, ids=[entry[0] for entry in PAGES])
async def test_a11y(page: Page, live_server, check_a11y, url_name: str, kwargs: dict):
    response = await page.goto(live_server.url + reverse(url_name, kwargs=kwargs))
    assert response is not None
    assert response.status == 200, f"{url_name} returned HTTP {response.status}"

    await check_a11y(page)
