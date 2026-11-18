from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

import pytest
from playwright.async_api import Page, expect

from froide.georegion.factories import GeoRegionFactory
from froide.publicbody.factories import (
    CategoryFactory,
    PublicBodyChangeProposalFactory,
    PublicBodyFactory,
)
from froide.publicbody.models import PublicBody

from .utils import do_login


def create_region():
    # The proposal forms only accept regions with level >= 1 that are no zipcodes
    return GeoRegionFactory.create(level=1, kind="state")


@pytest.fixture
def moderator(dummy_user):
    ct = ContentType.objects.get_for_model(PublicBody)
    perm = Permission.objects.get(content_type=ct, codename="moderate")
    dummy_user.user_permissions.add(perm)
    return dummy_user


@pytest.fixture
def publicbody():
    pb = PublicBodyFactory.create()
    pb.categories.set([CategoryFactory.create(), CategoryFactory.create()])
    pb.regions.set([create_region(), create_region()])
    return pb


def create_proposal(publicbody, categories, regions):
    proposal = PublicBodyChangeProposalFactory.create(publicbody=publicbody)
    proposal.categories.set(categories)
    proposal.regions.set(regions)
    return proposal


async def accept_proposal_on_page(page: Page, live_server, publicbody, proposal):
    await do_login(page, live_server)
    await page.goto(
        live_server.url + reverse("publicbody-accept", kwargs={"pk": publicbody.pk})
    )
    await expect(page.locator(".choices")).to_have_count(2)
    await page.locator(f"#proposal_id-{proposal.id}").check()


async def get_widget_values(page: Page, field: str):
    """Return the values shown as chips and the values that will be submitted."""
    chips = page.locator(
        f".choices:has(#id_{field}_select) .choices__list--multiple .choices__item"
    )
    chip_values = await chips.evaluate_all("els => els.map(el => el.dataset.value)")
    hidden_value = await page.locator(f"#id_{field}").input_value()
    submitted_values = [v for v in hidden_value.split(",") if v]
    return set(chip_values), set(submitted_values)


@pytest.mark.django_db
@pytest.mark.xdist_group(name="sequential")
@pytest.mark.asyncio(loop_scope="session")
async def test_accept_proposal(page: Page, live_server, moderator, publicbody):
    # Keep one existing value (Choices.js 11 would skip it as a duplicate)
    # and add a new one (Choices.js 11 would not select it)
    categories = [publicbody.categories.first(), CategoryFactory.create()]
    regions = [publicbody.regions.first(), create_region()]
    proposal = create_proposal(publicbody, categories, regions)

    await accept_proposal_on_page(page, live_server, publicbody, proposal)

    # The widgets show and submit the proposal's categories and regions
    expected_categories = {c.name for c in categories}
    expected_regions = {str(r.id) for r in regions}
    assert await get_widget_values(page, "categories") == (
        expected_categories,
        expected_categories,
    ), "category widget does not hold the proposal's categories"
    assert await get_widget_values(page, "regions") == (
        expected_regions,
        expected_regions,
    ), "region widget does not hold the proposal's regions"

    # Plain fields get the proposal's values, too
    await expect(page.locator("#id_email")).to_have_value(proposal.email)
    await expect(page.locator("#id_classification")).to_have_value(
        str(proposal.classification_id)
    )

    # Saving stores the proposal's categories and regions
    await page.get_by_role("button", name="Apply change").click()
    await expect(page.get_by_text("Your change has been applied.")).to_be_visible()

    publicbody.refresh_from_db()
    assert set(publicbody.categories.all()) == set(categories)
    assert set(publicbody.regions.all()) == set(regions)


@pytest.mark.django_db
@pytest.mark.xdist_group(name="sequential")
@pytest.mark.asyncio(loop_scope="session")
async def test_accept_empty_proposal(page: Page, live_server, moderator, publicbody):
    proposal = create_proposal(publicbody, [], [])

    await accept_proposal_on_page(page, live_server, publicbody, proposal)

    # No addItem event fires for an empty list, so the submitted inputs have to be
    # emptied explicitly
    assert await get_widget_values(page, "categories") == (set(), set())
    assert await get_widget_values(page, "regions") == (set(), set())
