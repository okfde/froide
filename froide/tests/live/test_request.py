import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone

import pytest
from playwright.sync_api import expect

from froide.foirequest.models import FoiRequest, RequestDraft
from froide.foirequest.tests import factories
from froide.publicbody.models import PublicBody

# import time


# from selenium.webdriver.support.ui import Select
# from selenium.webdriver.support.wait import WebDriverWait


User = get_user_model()


def go_to_make_request_url(page, live_server, pb=None):
    if pb is None:
        path = reverse("foirequest-make_request")
    else:
        path = reverse(
            "foirequest-make_request",
            kwargs={"publicbody_slug": pb.slug},
        )
    url = live_server.url + path
    page.goto(url=url)


def go_to_request_page(page, live_server, foirequest):
    path = reverse("foirequest-show", kwargs={"slug": foirequest.slug})
    page.goto(live_server.url + path)


def do_login(page, live_server, navigate=True):
    if navigate:
        page.goto(live_server.url + reverse("account-login"))
        user = User.objects.get(username="dummy")
        page.fill("[name=username]", user.email)
        page.fill("[name=password]", "froide")
        page.locator('button.btn.btn-primary[type="submit"]').click()
        expect(page.locator("#navbaraccount-link")).to_have_count(1)


@pytest.mark.django_db
def test_make_not_logged_in_request(page, live_server, public_body_with_index):
    pb = PublicBody.objects.all().first()
    go_to_make_request_url(page, live_server)
    page.locator(".search-public_bodies").fill(pb.name)
    page.locator(".search-public_bodies-submit").click()
    buttons = page.locator(".search-results .search-result .btn")
    expect(buttons).to_have_count(2)
    page.locator(".search-results .search-result .btn >> nth=0").click()

    req_title = "FoiRequest Number"
    page.fill("[name=subject]", req_title)
    page.fill("[name=body]", "Documents describing something...")
    page.fill("[name=first_name]", "Peter")
    page.fill("[name=last_name]", "Parker")
    user_email = "peter.parker@example.com"
    page.fill("[name=user_email]", user_email)
    page.locator("[name=terms]").click()
    page.locator("#review-button").click()

    mail.outbox = []
    page.locator("#send-request-button").click()

    new_account_url = reverse("account-new")
    assert new_account_url in page.url

    new_user = User.objects.get(email=user_email)
    assert not new_user.private
    req = FoiRequest.objects.get(user=new_user)
    assert req.title == req_title
    assert req.public
    assert req.public_body == pb
    assert req.status == FoiRequest.STATUS.AWAITING_USER_CONFIRMATION
    message = mail.outbox[0]
    match = re.search(r"http://[^/]+(/.+)", message.body)
    activate_url = match.group(1)
    page.goto("%s%s" % (live_server.url, activate_url))
    account_confirmed = reverse("account-confirmed")
    assert account_confirmed in page.url
    expect(page.locator("xpath=//h2")).to_have_text(
        "Your email address is now confirmed!"
    )
    req = FoiRequest.objects.get(user=new_user)
    assert req.status == "awaiting_response"


@pytest.mark.django_db
def test_make_not_logged_in_request_to_public_body(page, live_server, world):
    pb = PublicBody.objects.all().first()
    go_to_make_request_url(page, live_server, pb=pb)

    user_first_name = "Peter"
    user_last_name = "Parker"
    req_title = "FoiRequest Number"
    page.fill("[name=subject]", req_title)
    page.fill("[name=body]", "Documents describing something...")
    page.fill("[name=first_name]", user_first_name)
    page.fill("[name=last_name]", user_last_name)
    user_email = "peter.parker@example.com"
    page.fill("[name=user_email]", user_email)
    page.locator("[name=terms]").click()
    page.locator("#review-button").click()
    page.locator("#send-request-button").click()

    new_account_url = reverse("account-new")
    assert new_account_url in page.url
    new_user = User.objects.get(email=user_email)
    assert new_user.first_name == user_first_name
    assert new_user.last_name == user_last_name
    assert not new_user.private
    req = FoiRequest.objects.get(user=new_user)
    assert req.title == req_title
    assert req.public
    assert req.public_body == pb
    assert req.status == FoiRequest.STATUS.AWAITING_USER_CONFIRMATION


@pytest.mark.django_db
def test_make_logged_in_request(page, live_server, public_body_with_index, dummy_user):
    do_login(page, live_server)
    assert dummy_user.is_authenticated
    go_to_make_request_url(page, live_server)
    pb = PublicBody.objects.all().first()
    page.locator(".search-public_bodies").fill(pb.name)
    page.locator(".search-public_bodies-submit").click()
    buttons = page.locator(".search-results .search-result .btn")
    expect(buttons).to_have_count(2)
    page.locator(".search-results .search-result .btn >> nth=0").click()

    req_title = "FoiRequest Number"
    body_text = "Documents describing & something..."
    page.fill("[name=subject]", req_title)
    page.fill("[name=body]", body_text)
    page.locator("#review-button").click()
    page.locator("#send-request-button").click()
    request_sent = reverse("foirequest-request_sent")
    assert request_sent in page.url
    req = FoiRequest.objects.filter(user=dummy_user).order_by("-id")[0]
    assert req.title == req_title
    assert req.description in body_text
    assert body_text, req.messages[0].plaintext
    assert req.public
    assert req.public_body == pb
    assert req.status == "awaiting_response"


@pytest.mark.django_db
def test_make_logged_in_request_too_many(
    page,
    live_server,
    foi_request_factory,
    foi_message_factory,
    world,
    request_throttle_settings,
):
    dummy_user = User.objects.get(username="dummy")
    for _i in range(5):
        req = foi_request_factory(
            user=dummy_user,
            first_message=timezone.now(),
        )
        foi_message_factory(request=req, is_response=False, sender_user=dummy_user)
    do_login(page, live_server)
    pb = PublicBody.objects.all().first()
    go_to_make_request_url(page, live_server, pb=pb)
    req_title = "FoiRequest Number"
    body_text = "Documents describing & something..."
    page.fill("[name=subject]", req_title)
    page.fill("[name=body]", body_text)
    page.locator("#review-button").click()
    page.locator("#send-request-button").click()
    make_request = reverse("foirequest-make_request")
    assert make_request in page.url
    alert = page.locator(".alert-danger")
    expect(alert).to_contain_text("exceeded your request limit")


@pytest.mark.django_db
def test_make_request_logged_out_with_existing_account(page, live_server, world):
    pb = PublicBody.objects.all().first()
    user = User.objects.get(username="dummy")
    go_to_make_request_url(page, live_server, pb=pb)
    req_title = "FoiRequest Number"
    body_text = "Documents describing & something..."
    user_first_name = user.first_name
    user_last_name = user.last_name
    page.fill("[name=subject]", req_title)
    page.fill("[name=body]", body_text)
    page.fill("[name=first_name]", user_first_name)
    page.fill("[name=last_name]", user_last_name)
    page.fill("[name=user_email]", user.email)
    page.locator("[name=terms]").click()
    page.locator("[name=public]").click()
    page.locator("[name=private]").click()
    page.locator("#review-button").click()

    old_count = FoiRequest.objects.filter(user=user).count()
    draft_count = RequestDraft.objects.filter(user=None).count()
    page.locator("#send-request-button").click()

    new_account_url = reverse("account-new")
    assert new_account_url in page.url

    new_count = FoiRequest.objects.filter(user=user).count()
    assert old_count == new_count
    new_draft_count = RequestDraft.objects.filter(user=None).count()
    assert draft_count + 1 == new_draft_count
    req = RequestDraft.objects.get(user=None)
    assert req.title == req_title
    assert not req.public
    assert pb in req.publicbodies.all()


@pytest.mark.django_db
def test_collapsed_menu(page, live_server):
    SCREEN_SIZE = (400, 800)
    page.set_viewport_size({"width": SCREEN_SIZE[0], "height": SCREEN_SIZE[1]})
    page.goto(live_server.url + reverse("index"))
    expect(page.locator(".navbar form[role=search]")).not_to_be_visible()
    page.locator(".navbar-toggler").click()
    expect(page.locator(".navbar form[role=search]")).to_be_visible()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "from_resolution, to_resolution",
    [
        ("", "successful"),
        ("successful", "refused"),
        ("refused", "partially_successful"),
    ],
)
def test_set_status(
    page,
    live_server,
    world,
    foi_request_factory,
    foi_message_factory,
    from_resolution,
    to_resolution,
):
    factories.rebuild_index()
    user = User.objects.get(username="dummy")
    req = foi_request_factory(
        user=user, first_message=timezone.now(), status="resolved"
    )
    foi_message_factory(request=req, is_response=False, sender_user=user)
    do_login(page, live_server)
    req.refresh_from_db()
    assert req.resolution == from_resolution
    go_to_request_page(req)
    expect(page.locator(".info-box__edit-panel > form")).not_to_be_visible()
    page.locator("info-box__edit-button").click()
    expect(page.locator(".info-box__edit-panel > form")).to_be_visible()

    resolution_select = page.locator("#id_resolution")
    expect(resolution_select).to_be_visible()
    expect(page.locator('#id_resolution > option[selected="selected"]')).to_have_text(
        from_resolution
    )

    # self.assertEquals(
    #     resolution_select.first_selected_option.get_attribute("value"),
    #     from_resolution,
    # )
    # reason = page.locator("#id_refusal_reason")

    # resolution_select.select_by_value("successful")
    # time.sleep(1)
    # self.assertFalse(reason.is_displayed())

    # resolution_select.select_by_value("refused")
    # time.sleep(1)
    # self.assertTrue(reason.is_displayed())

    # resolution_select.select_by_value(to_resolution)
    # self.scrollTo("set-status-submit")
    # editForm.find_element_by_id("set-status-submit").click()

    # self.req.refresh_from_db()
    # self.assertEquals(self.req.resolution, to_resolution)


# @tag("ui", "slow")
# class TestSettingStatus(LiveTestMixin, StaticLiveServerTestCase):
#     def setUp(self):
#         factories.make_world()
#         factories.rebuild_index()
#         self.user = User.objects.get(username="dummy")

#         self.req: FoiRequest = factories.FoiRequestFactory.create(
#             user=self.user, first_message=timezone.now(), status="resolved"
#         )
#         factories.FoiMessageFactory.create(
#             request=self.req, is_response=False, sender_user=self.user
#         )


#     def test_set_status(self):
#         self.do_login()

#                 resolution = self.selenium.find_element_by_id("id_resolution")
#                 resolution_select = Select(resolution)
#                 reason = self.selenium.find_element_by_id("id_refusal_reason")
#                 self.assertTrue(resolution.is_displayed())
#                 self.assertEquals(
#                     resolution_select.first_selected_option.get_attribute("value"),
#                     from_resolution,
#                 )

#                 resolution_select.select_by_value("successful")
#                 time.sleep(1)
#                 self.assertFalse(reason.is_displayed())

#                 resolution_select.select_by_value("refused")
#                 time.sleep(1)
#                 self.assertTrue(reason.is_displayed())

#                 resolution_select.select_by_value(to_resolution)
#                 self.scrollTo("set-status-submit")
#                 editForm.find_element_by_id("set-status-submit").click()

#                 self.req.refresh_from_db()
#                 self.assertEquals(self.req.resolution, to_resolution)
