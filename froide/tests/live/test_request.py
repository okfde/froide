import logging
import re
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail
from django.test import tag
from django.urls import reverse
from django.utils import timezone

from selenium.webdriver.support.wait import WebDriverWait

from froide.foirequest.models import FoiRequest, RequestDraft
from froide.foirequest.tests import factories
from froide.publicbody.models import PublicBody

from . import CheckJSErrors, LiveTestMixin

User = get_user_model()


@tag("ui", "slow")
class TestMakingRequest(LiveTestMixin, StaticLiveServerTestCase):
    def setUp(self):
        factories.make_world()
        factories.rebuild_index()
        self.user = User.objects.get(username="dummy")
        self.pb = PublicBody.objects.all()[0]

    def go_to_make_request_url(self, pb=None):
        if pb is None:
            path = reverse("foirequest-make_request")
        else:
            path = reverse(
                "foirequest-make_request", kwargs={"publicbody_ids": str(pb.pk)}
            )
        self.selenium.get("%s%s" % (self.live_server_url, path))

    def do_login(self, navigate=True):
        if navigate:
            self.selenium.get("%s%s" % (self.live_server_url, reverse("account-login")))
        email_input = self.selenium.find_element_by_name("username")
        email_input.send_keys(self.user.email)
        password_input = self.selenium.find_element_by_name("password")
        password_input.send_keys("froide")
        self.selenium.find_element_by_xpath(
            '//form//button[contains(text(), "Log In")]'
        ).click()

    def test_make_not_logged_in_request(self):
        self.go_to_make_request_url()
        with CheckJSErrors(self.selenium):
            search_pbs = self.selenium.find_element_by_class_name(
                "search-public_bodies"
            )
            search_pbs.send_keys(self.pb.name)
            self.selenium.find_element_by_class_name(
                "search-public_bodies-submit"
            ).click()
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_css_selector(
                    ".search-results .search-result"
                )
            )
            self.selenium.find_element_by_css_selector(
                ".search-results .search-result .btn"
            ).click()
            req_title = "FoiRequest Number"
            self.selenium.find_element_by_name("subject").send_keys(req_title)
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_name("body").is_displayed()
            )
            self.selenium.find_element_by_name("body").send_keys(
                "Documents describing something..."
            )
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_elements_by_css_selector(
                    ".similar-requests li"
                )
            )
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_id("review-button").is_displayed()
            )
            self.selenium.find_element_by_name("first_name").send_keys("Peter")
            self.selenium.find_element_by_name("last_name").send_keys("Parker")
            user_email = "peter.parker@example.com"
            self.selenium.find_element_by_name("user_email").send_keys(user_email)
            self.scrollTo("id_terms")
            self.selenium.find_element_by_name("terms").click()
            self.selenium.find_element_by_id("review-button").click()
            self.selenium.find_element_by_id("step-review")
            self.scrollTo("send-request-button")

        mail.outbox = []
        self.selenium.find_element_by_id("send-request-button").click()

        new_account_url = reverse("account-new")
        WebDriverWait(self.selenium, 5).until(
            lambda driver: new_account_url in driver.current_url
        )
        self.assertIn(new_account_url, self.selenium.current_url)

        new_user = User.objects.get(email=user_email)
        self.assertEqual(new_user.private, False)
        req = FoiRequest.objects.get(user=new_user)
        self.assertEqual(req.title, req_title)
        self.assertEqual(req.public, True)
        self.assertEqual(req.public_body, self.pb)
        self.assertEqual(req.status, FoiRequest.STATUS.AWAITING_USER_CONFIRMATION)
        message = mail.outbox[0]
        match = re.search(r"http://[^/]+(/.+)", message.body)
        activate_url = match.group(1)
        self.selenium.get("%s%s" % (self.live_server_url, activate_url))
        account_confirmed = reverse("account-confirmed")

        WebDriverWait(self.selenium, 5).until(
            lambda driver: account_confirmed in driver.current_url
        )
        self.assertIn(account_confirmed, self.selenium.current_url)
        headline = self.selenium.find_element_by_xpath(
            '//h2[contains(text(), "Your email address is now confirmed!")]'
        )
        self.assertTrue(headline)
        req = FoiRequest.objects.get(user=new_user)
        self.assertEqual(req.status, "awaiting_response")

    def test_make_not_logged_in_request_to_public_body(self):
        self.go_to_make_request_url(pb=self.pb)

        with CheckJSErrors(self.selenium):
            req_title = "FoiRequest Number"
            self.selenium.find_element_by_name("subject").send_keys(req_title)
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_name("body").is_displayed()
            )
            self.selenium.find_element_by_name("body").send_keys(
                "Documents describing something..."
            )
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_elements_by_css_selector(
                    ".similar-requests li"
                )
            )
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_id("review-button").is_displayed()
            )
            user_first_name = "Peter"
            user_last_name = "Parker"
            self.selenium.find_element_by_name("first_name").send_keys(user_first_name)
            self.selenium.find_element_by_name("last_name").send_keys(user_last_name)
            user_email = "peter.parker@example.com"
            self.selenium.find_element_by_name("user_email").send_keys(user_email)
            self.scrollTo("id_terms")
            self.selenium.find_element_by_name("terms").click()
            self.selenium.find_element_by_name("public").click()
            self.scrollTo("id_private")
            self.selenium.find_element_by_name("private").click()
            self.scrollTo("review-button")
            self.selenium.find_element_by_id("review-button").click()
            self.scrollTo("send-request-button")

        self.selenium.find_element_by_id("send-request-button").click()

        new_account_url = reverse("account-new")
        WebDriverWait(self.selenium, 5).until(
            lambda driver: new_account_url in driver.current_url
        )
        self.assertIn(new_account_url, self.selenium.current_url)

        new_user = User.objects.get(email=user_email)
        self.assertEqual(new_user.first_name, user_first_name)
        self.assertEqual(new_user.last_name, user_last_name)
        self.assertEqual(new_user.private, True)
        req = FoiRequest.objects.get(user=new_user)
        self.assertEqual(req.title, req_title)
        self.assertEqual(req.public, False)
        self.assertEqual(req.public_body, self.pb)
        self.assertEqual(req.status, FoiRequest.STATUS.AWAITING_USER_CONFIRMATION)

    def test_make_logged_in_request(self):
        self.do_login()
        self.go_to_make_request_url()

        with CheckJSErrors(self.selenium):
            search_pbs = self.selenium.find_element_by_class_name(
                "search-public_bodies"
            )
            search_pbs.send_keys(self.pb.name)
            self.selenium.find_element_by_class_name(
                "search-public_bodies-submit"
            ).click()
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_css_selector(
                    ".search-results .search-result"
                )
            )
            self.selenium.find_element_by_css_selector(
                ".search-results .search-result .btn"
            ).click()
            req_title = "FoiRequest Number"
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_name("body").is_displayed()
            )
            self.selenium.find_element_by_name("subject").send_keys(req_title)
            self.scrollTo("id_body")
            self.selenium.find_element_by_name("body").clear()
            body_text = "Documents describing & something..."
            self.selenium.find_element_by_name("body").send_keys(body_text)
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_elements_by_css_selector(
                    ".similar-requests li"
                )
            )
            self.scrollTo("review-button")
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_id("review-button").is_displayed()
            )
            self.selenium.find_element_by_id("review-button").click()
            self.scrollTo("send-request-button")

        WebDriverWait(self.selenium, 10).until(
            lambda driver: self.selenium.find_element_by_id(
                "send-request-button"
            ).is_displayed()
        )
        self.selenium.find_element_by_id("send-request-button").click()

        request_sent = reverse("foirequest-request_sent")
        WebDriverWait(self.selenium, 5).until(
            lambda driver: request_sent in driver.current_url
        )

        self.assertIn(request_sent, self.selenium.current_url)

        req = FoiRequest.objects.filter(user=self.user).order_by("-id")[0]
        self.assertEqual(req.title, req_title)
        self.assertIn(req.description, body_text)
        self.assertIn(body_text, req.messages[0].plaintext)
        self.assertEqual(req.public, True)
        self.assertEqual(req.public_body, self.pb)
        self.assertEqual(req.status, "awaiting_response")

    def test_make_logged_in_request_too_many(self):
        for _i in range(5):
            req = factories.FoiRequestFactory.create(
                user=self.user,
                first_message=timezone.now(),
            )
            factories.FoiMessageFactory.create(
                request=req, is_response=False, sender_user=self.user
            )

        froide_config = settings.FROIDE_CONFIG
        froide_config["request_throttle"] = [(2, 60), (5, 60 * 60)]

        with self.settings(FROIDE_CONFIG=froide_config):

            self.do_login()
            self.go_to_make_request_url(pb=self.pb)

            with CheckJSErrors(self.selenium):
                req_title = "FoiRequest Number"
                WebDriverWait(self.selenium, 5).until(
                    lambda driver: driver.find_element_by_name("body").is_displayed()
                )
                self.selenium.find_element_by_name("subject").send_keys(req_title)
                self.scrollTo("id_body")
                self.selenium.find_element_by_name("body").clear()
                body_text = "Documents describing & something..."
                self.selenium.find_element_by_name("body").send_keys(body_text)
                WebDriverWait(self.selenium, 5).until(
                    lambda driver: driver.find_elements_by_css_selector(
                        ".similar-requests li"
                    )
                )
                self.scrollTo("review-button")
                WebDriverWait(self.selenium, 5).until(
                    lambda driver: driver.find_element_by_id(
                        "review-button"
                    ).is_displayed()
                )
                self.selenium.find_element_by_id("review-button").click()
                self.scrollTo("send-request-button")

            WebDriverWait(self.selenium, 10).until(
                lambda driver: self.selenium.find_element_by_id(
                    "send-request-button"
                ).is_displayed()
            )

            self.selenium.find_element_by_id("send-request-button").click()
            make_request = reverse("foirequest-make_request")
            self.assertIn(make_request, self.selenium.current_url)

            alert_text = self.selenium.find_element_by_css_selector(
                ".alert.alert-danger"
            ).text
            self.assertIn("exceeded your request limit", alert_text)

    def test_make_request_logged_out_with_existing_account(self):
        self.go_to_make_request_url(pb=self.pb)
        with CheckJSErrors(self.selenium):
            req_title = "FoiRequest Number"
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_name("body").is_displayed()
            )
            self.selenium.find_element_by_name("subject").send_keys(req_title)
            self.selenium.find_element_by_name("body").send_keys(
                "Documents describing something..."
            )
            user_first_name = self.user.first_name
            user_last_name = self.user.last_name
            self.selenium.find_element_by_name("first_name").send_keys(user_first_name)
            self.selenium.find_element_by_name("last_name").send_keys(user_last_name)
            self.selenium.find_element_by_name("user_email").send_keys(self.user.email)
            self.scrollTo("id_terms")
            self.selenium.find_element_by_name("terms").click()
            self.selenium.find_element_by_name("public").click()
            self.scrollTo("id_private")
            self.selenium.find_element_by_name("private").click()

            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_elements_by_css_selector(
                    ".similar-requests li"
                )
            )
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_id("review-button").is_displayed()
            )
            self.scrollTo("review-button")
            self.selenium.find_element_by_id("review-button").click()
            self.scrollTo("send-request-button")

        WebDriverWait(self.selenium, 10).until(
            lambda driver: self.selenium.find_element_by_id(
                "send-request-button"
            ).is_displayed()
        )

        old_count = FoiRequest.objects.filter(user=self.user).count()
        draft_count = RequestDraft.objects.filter(user=None).count()
        self.selenium.find_element_by_id("send-request-button").click()

        new_account_url = reverse("account-new")
        WebDriverWait(self.selenium, 5).until(
            lambda driver: new_account_url in driver.current_url
        )
        self.assertIn(new_account_url, self.selenium.current_url)

        new_count = FoiRequest.objects.filter(user=self.user).count()
        self.assertEqual(old_count, new_count)
        new_draft_count = RequestDraft.objects.filter(user=None).count()
        self.assertEqual(draft_count + 1, new_draft_count)

        req = RequestDraft.objects.get(user=None)
        self.assertEqual(req.title, req_title)
        self.assertEqual(req.public, False)
        self.assertIn(self.pb, req.publicbodies.all())


@tag("ui", "slow")
class MenuTest(LiveTestMixin, StaticLiveServerTestCase):
    SCREEN_SIZE = (400, 800)
    ADDITIONAL_KWARGS = {"window-size": "%s,%s" % SCREEN_SIZE}

    def test_collapsed_menu(self):
        try:
            self.selenium.set_window_size(*self.SCREEN_SIZE)
        except Exception as e:
            logging.exception(e)
        logging.warning("Window size: %s", self.selenium.get_window_size())
        with CheckJSErrors(self.selenium):
            self.selenium.get("%s%s" % (self.live_server_url, reverse("index")))
            search_form = self.selenium.find_element_by_css_selector(
                ".navbar form[role=search]"
            )
            self.assertFalse(search_form.is_displayed())
            self.selenium.find_element_by_css_selector(".navbar-toggler").click()
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_css_selector(
                    ".navbar form[role=search]"
                ).is_displayed()
            )
            time.sleep(0.5)
            self.selenium.find_element_by_css_selector(".navbar-toggler").click()
            WebDriverWait(self.selenium, 5).until(
                lambda driver: not driver.find_element_by_css_selector(
                    ".navbar form[role=search]"
                ).is_displayed()
            )
