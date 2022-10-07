# import logging
import re

# from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail
from django.test import tag
from django.urls import reverse

from playwright.sync_api import expect, sync_playwright

from froide.foirequest.models import FoiRequest
from froide.foirequest.tests import factories
from froide.publicbody.models import PublicBody

from . import LiveTestMixin

# import time

# from django.utils import timezone

# from selenium.webdriver.support.ui import Select
# from selenium.webdriver.support.wait import WebDriverWait


User = get_user_model()


@tag("ui", "slow")
class TestMakingRequest(LiveTestMixin, StaticLiveServerTestCase):
    @classmethod
    def setup_class(cls):
        factories.make_world()
        factories.rebuild_index()
        cls.user = User.objects.get(username="dummy")
        cls.pb = PublicBody.objects.all().first()
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=False)

    @classmethod
    def teardown_class(cls):
        super().tearDownClass()
        cls.browser.close()
        cls.playwright.stop()

    def go_to_make_request_url(self, page, pb=None):
        if pb is None:
            path = reverse("foirequest-make_request")
        else:
            path = reverse(
                "foirequest-make_request",
                kwargs={"publicbody_ids": "{}+".format(pb.slug)},
            )
        url = self.live_server_url + path
        page.goto(url=url)

    def do_login(self, page, navigate=True):
        if navigate:
            page.goto(self.live_server_url + reverse("account-login"))
        user = User.objects.get(username="dummy")
        page.fill("[name=username]", user.email)
        page.fill("[name=password]", "froide")
        page.click("text=Log in")

    def test_make_not_logged_in_request(self):
        page = self.browser.new_page()
        self.go_to_make_request_url(page)
        page.locator(".search-public_bodies").fill(self.pb.name)
        page.locator(".search-public_bodies-submit").click()
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
        page.locator("#step-review")

        mail.outbox = []
        page.locator("#send-request-button").click()

        new_account_url = reverse("account-new")
        self.assertIn(new_account_url, page.url)

        new_user = User.objects.get(email=user_email)
        assert not new_user.private
        req = FoiRequest.objects.get(user=new_user)
        assert req.title == req_title
        assert req.public
        assert req.public_body == self.pb
        assert req.status == FoiRequest.STATUS.AWAITING_USER_CONFIRMATION
        message = mail.outbox[0]
        match = re.search(r"http://[^/]+(/.+)", message.body)
        activate_url = match.group(1)
        page.goto("%s%s" % (self.live_server_url, activate_url))
        account_confirmed = reverse("account-confirmed")
        assert account_confirmed in page.url
        expect(page.locator("xpath=//h2")).to_have_text(
            "Your email address is now confirmed!"
        )
        req = FoiRequest.objects.get(user=new_user)
        assert req.status == "awaiting_response"

    def test_make_not_logged_in_request_to_public_body(self):
        page = self.browser.new_page()
        self.go_to_make_request_url(page, pb=self.pb)

        user_first_name = "Peter"
        user_last_name = "Parker"

        req_title = "FoiRequest Number"
        page.fill("[name=subject]", req_title)
        page.fill("[name=body]", "Documents describing something...")
        page.fill("[name=first_name]", user_first_name)
        page.fill("[name=last_name]", "Parker")
        user_email = "peter.parker@example.com"
        page.fill("[name=user_email]", user_email)

        page.locator("[name=terms]").click()
        page.locator("[name=public]").click()
        page.locator("[name=private]").click()
        page.locator("#review-button").click()
        page.locator("#send-request-button").click()

        new_account_url = reverse("account-new")
        self.assertIn(new_account_url, page.url)

        new_user = User.objects.get(email=user_email)
        assert new_user.first_name == user_first_name
        assert new_user.last_name == user_last_name
        assert new_user.private
        req = FoiRequest.objects.get(user=new_user)
        self.assertEqual(req.title, req_title)
        self.assertEqual(req.public, False)
        self.assertEqual(req.public_body, self.pb)
        self.assertEqual(req.status, FoiRequest.STATUS.AWAITING_USER_CONFIRMATION)

    # def test_make_logged_in_request(self):
    #     self.do_login()
    #     self.go_to_make_request_url()

    #     with CheckJSErrors(self.selenium):
    #         search_pbs = self.selenium.find_element_by_class_name(
    #             "search-public_bodies"
    #         )
    #         search_pbs.send_keys(self.pb.name)
    #         self.selenium.find_element_by_class_name(
    #             "search-public_bodies-submit"
    #         ).click()
    #         WebDriverWait(self.selenium, 5).until(
    #             lambda driver: driver.find_element_by_css_selector(
    #                 ".search-results .search-result"
    #             )
    #         )
    #         self.selenium.find_element_by_css_selector(
    #             ".search-results .search-result .btn"
    #         ).click()
    #         req_title = "FoiRequest Number"
    #         WebDriverWait(self.selenium, 5).until(
    #             lambda driver: driver.find_element_by_name("body").is_displayed()
    #         )
    #         self.selenium.find_element_by_name("subject").send_keys(req_title)
    #         self.scrollTo("id_body")
    #         self.selenium.find_element_by_name("body").clear()
    #         body_text = "Documents describing & something..."
    #         self.selenium.find_element_by_name("body").send_keys(body_text)
    #         WebDriverWait(self.selenium, 5).until(
    #             lambda driver: driver.find_elements_by_css_selector(
    #                 ".similar-requests li"
    #             )
    #         )
    #         self.scrollTo("review-button")
    #         self.selenium.find_element_by_id("review-button").click()
    #         self.scrollTo("send-request-button")

    #     self.selenium.find_element_by_id("send-request-button").click()

    #     request_sent = reverse("foirequest-request_sent")
    #     WebDriverWait(self.selenium, 5).until(
    #         lambda driver: request_sent in driver.current_url
    #     )

    #     self.assertIn(request_sent, self.selenium.current_url)

    #     req = FoiRequest.objects.filter(user=self.user).order_by("-id")[0]
    #     self.assertEqual(req.title, req_title)
    #     self.assertIn(req.description, body_text)
    #     self.assertIn(body_text, req.messages[0].plaintext)
    #     self.assertEqual(req.public, True)
    #     self.assertEqual(req.public_body, self.pb)
    #     self.assertEqual(req.status, "awaiting_response")

    # def test_make_logged_in_request_too_many(self):
    #     for _i in range(5):
    #         req = factories.FoiRequestFactory.create(
    #             user=self.user,
    #             first_message=timezone.now(),
    #         )
    #         factories.FoiMessageFactory.create(
    #             request=req, is_response=False, sender_user=self.user
    #         )

    #     froide_config = settings.FROIDE_CONFIG
    #     froide_config["request_throttle"] = [(2, 60), (5, 60 * 60)]

    #     with self.settings(FROIDE_CONFIG=froide_config):

    #         self.do_login()
    #         self.go_to_make_request_url(pb=self.pb)

    #         with CheckJSErrors(self.selenium):
    #             req_title = "FoiRequest Number"
    #             WebDriverWait(self.selenium, 5).until(
    #                 lambda driver: driver.find_element_by_name("body").is_displayed()
    #             )
    #             self.selenium.find_element_by_name("subject").send_keys(req_title)
    #             self.scrollTo("id_body")
    #             self.selenium.find_element_by_name("body").clear()
    #             body_text = "Documents describing & something..."
    #             self.selenium.find_element_by_name("body").send_keys(body_text)
    #             WebDriverWait(self.selenium, 5).until(
    #                 lambda driver: driver.find_elements_by_css_selector(
    #                     ".similar-requests li"
    #                 )
    #             )
    #             self.scrollTo("review-button")
    #             self.selenium.find_element_by_id("review-button").click()
    #             self.scrollTo("send-request-button")

    #         self.selenium.find_element_by_id("send-request-button").click()
    #         make_request = reverse("foirequest-make_request")
    #         self.assertIn(make_request, self.selenium.current_url)

    #         alert_text = self.selenium.find_element_by_css_selector(
    #             ".alert.alert-danger"
    #         ).text
    #         self.assertIn("exceeded your request limit", alert_text)

    # def test_make_request_logged_out_with_existing_account(self):
    #     self.go_to_make_request_url(pb=self.pb)
    #     with CheckJSErrors(self.selenium):
    #         req_title = "FoiRequest Number"
    #         WebDriverWait(self.selenium, 5).until(
    #             lambda driver: driver.find_element_by_name("body").is_displayed()
    #         )
    #         self.selenium.find_element_by_name("subject").send_keys(req_title)
    #         self.selenium.find_element_by_name("body").send_keys(
    #             "Documents describing something..."
    #         )
    #         user_first_name = self.user.first_name
    #         user_last_name = self.user.last_name
    #         self.selenium.find_element_by_name("first_name").send_keys(user_first_name)
    #         self.selenium.find_element_by_name("last_name").send_keys(user_last_name)
    #         self.selenium.find_element_by_name("user_email").send_keys(self.user.email)
    #         self.scrollTo("id_terms")
    #         self.selenium.find_element_by_name("terms").click()
    #         self.selenium.find_element_by_name("public").click()
    #         self.scrollTo("id_private")
    #         self.selenium.find_element_by_name("private").click()

    #         WebDriverWait(self.selenium, 5).until(
    #             lambda driver: driver.find_elements_by_css_selector(
    #                 ".similar-requests li"
    #             )
    #         )
    #         self.scrollTo("review-button")
    #         self.selenium.find_element_by_id("review-button").click()
    #         self.scrollTo("send-request-button")

    #     WebDriverWait(self.selenium, 10).until(
    #         lambda driver: self.selenium.find_element_by_id(
    #             "send-request-button"
    #         ).is_displayed()
    #     )

    #     old_count = FoiRequest.objects.filter(user=self.user).count()
    #     draft_count = RequestDraft.objects.filter(user=None).count()
    #     self.selenium.find_element_by_id("send-request-button").click()

    #     new_account_url = reverse("account-new")
    #     WebDriverWait(self.selenium, 5).until(
    #         lambda driver: new_account_url in driver.current_url
    #     )
    #     self.assertIn(new_account_url, self.selenium.current_url)

    #     new_count = FoiRequest.objects.filter(user=self.user).count()
    #     self.assertEqual(old_count, new_count)
    #     new_draft_count = RequestDraft.objects.filter(user=None).count()
    #     self.assertEqual(draft_count + 1, new_draft_count)

    #     req = RequestDraft.objects.get(user=None)
    #     self.assertEqual(req.title, req_title)
    #     self.assertEqual(req.public, False)
    #     self.assertIn(self.pb, req.publicbodies.all())


# @tag("ui", "slow")
# class MenuTest(LiveTestMixin, StaticLiveServerTestCase):
#     SCREEN_SIZE = (400, 800)
#     ADDITIONAL_KWARGS = {"window-size": "%s,%s" % SCREEN_SIZE}

#     def test_collapsed_menu(self):
#         try:
#             self.selenium.set_window_size(*self.SCREEN_SIZE)
#         except Exception as e:
#             logging.exception(e)
#         logging.warning("Window size: %s", self.selenium.get_window_size())
#         with CheckJSErrors(self.selenium):
#             self.selenium.get("%s%s" % (self.live_server_url, reverse("index")))
#             search_form = self.selenium.find_element_by_css_selector(
#                 ".navbar form[role=search]"
#             )
#             self.assertFalse(search_form.is_displayed())
#             self.selenium.find_element_by_css_selector(".navbar-toggler").click()
#             WebDriverWait(self.selenium, 5).until(
#                 lambda driver: driver.find_element_by_css_selector(
#                     ".navbar form[role=search]"
#                 ).is_displayed()
#             )
#             time.sleep(0.5)
#             self.selenium.find_element_by_css_selector(".navbar-toggler").click()
#             WebDriverWait(self.selenium, 5).until(
#                 lambda driver: not driver.find_element_by_css_selector(
#                     ".navbar form[role=search]"
#                 ).is_displayed()
#             )


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

#     def go_to_request_page(self, req: FoiRequest):
#         path = reverse("foirequest-show", kwargs={"slug": req.slug})
#         self.selenium.get("%s%s" % (self.live_server_url, path))

#     def do_login(self, navigate=True):
#         if navigate:
#             self.selenium.get("%s%s" % (self.live_server_url, reverse("account-login")))
#         email_input = self.selenium.find_element_by_name("username")
#         email_input.send_keys(self.user.email)
#         password_input = self.selenium.find_element_by_name("password")
#         password_input.send_keys("froide")
#         self.selenium.find_element_by_xpath(
#             '//form//button[contains(text(), "Log In")]'
#         ).click()

#     def test_set_status(self):
#         self.do_login()

#         for from_resolution, to_resolution in [
#             ("", "successful"),
#             ("successful", "refused"),
#             ("refused", "partially_successful"),
#         ]:
#             self.req.refresh_from_db()
#             self.assertEquals(self.req.resolution, from_resolution)

#             self.go_to_request_page(self.req)

#             with CheckJSErrors(self.selenium):
#                 WebDriverWait(self.selenium, 5).until(
#                     lambda driver: driver.find_element_by_class_name(
#                         "info-box__edit-button"
#                     ).is_displayed()
#                 )
#                 editForm = self.selenium.find_element_by_css_selector(
#                     ".info-box__edit-panel > form"
#                 )
#                 self.assertFalse(editForm.is_displayed())
#                 self.selenium.find_element_by_class_name(
#                     "info-box__edit-button"
#                 ).click()
#                 time.sleep(1)
#                 self.assertTrue(editForm.is_displayed())
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
