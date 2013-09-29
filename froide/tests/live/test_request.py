import time

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import LiveServerTestCase
from django.contrib.auth.models import User

from selenium.webdriver.support.wait import WebDriverWait

from froide.foirequest.tests import factories
from froide.foirequest.models import FoiRequest
from froide.publicbody.models import PublicBody


def get_selenium():
    driver = getattr(settings, 'TEST_SELENIUM_DRIVER', 'firefox')
    if driver == 'chrome':
        from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
        return ChromeDriver()
    elif driver == 'phantomjs':
        from selenium.webdriver import PhantomJS
        return PhantomJS()
    else:
        from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxDriver
        return FirefoxDriver()


class TestMakingRequest(LiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        cls.selenium = get_selenium()
        cls.selenium.implicitly_wait(10)
        super(TestMakingRequest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(TestMakingRequest, cls).tearDownClass()

    def setUp(self):
        factories.make_world()
        factories.rebuild_index()
        self.do_logout()
        self.user = User.objects.all()[0]
        self.pb = PublicBody.objects.all()[0]

    def do_login(self, navigate=True):
        if navigate:
            self.selenium.get('%s%s' % (self.live_server_url, reverse('account-login')))
        email_input = self.selenium.find_element_by_id("id_email")
        email_input.send_keys(self.user.email)
        password_input = self.selenium.find_element_by_id("id_password")
        password_input.send_keys('froide')
        self.selenium.find_element_by_xpath(
            '//form/button[.="Log In"]').click()

    def do_logout(self):
        self.selenium.get('%s%s' % (self.live_server_url, reverse('account-logout')))

    def test_make_not_logged_in_request(self):
        self.selenium.get('%s%s' % (self.live_server_url,
            reverse('foirequest-make_request')))
        search_pbs = self.selenium.find_element_by_id('id_public_body')
        search_pbs.send_keys(self.pb.name)
        self.selenium.find_element_by_class_name('search-public_bodies-submit').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('.search-results .result'))
        self.selenium.find_element_by_css_selector('.search-results .result label').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_id('option-check_foi').is_displayed())
        self.selenium.find_element_by_id('option-check_foi').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_id('continue-foicheck'))
        self.selenium.find_element_by_id('continue-foicheck').click()
        req_title = 'FoiRequest Number'
        self.selenium.find_element_by_id('id_subject').send_keys(req_title)
        self.selenium.find_element_by_id('id_body').send_keys('Documents describing something...')
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_elements_by_css_selector('#similar-requests li'))
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_id('review-button').is_displayed()
        )
        self.selenium.find_element_by_id('id_first_name')\
            .send_keys('Peter')
        self.selenium.find_element_by_id('id_last_name')\
            .send_keys('Parker')
        user_email = 'peter.parker@example.com'
        self.selenium.find_element_by_id('id_user_email')\
            .send_keys(user_email)
        self.selenium.find_element_by_id('id_terms').click()
        self.selenium.find_element_by_id('review-button').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('#review-text .highlight'))
        time.sleep(0.5)
        self.selenium.find_element_by_id('send-request-button').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('.heroine-unit'))
        new_user = User.objects.get(email=user_email)
        self.assertEqual(new_user.get_profile().private, False)
        req = FoiRequest.objects.get(user=new_user)
        self.assertEqual(req.title, req_title)
        self.assertEqual(req.public, True)
        self.assertEqual(req.public_body, self.pb)
        self.assertEqual(req.status, 'awaiting_user_confirmation')

    def test_make_not_logged_in_request_to_public_body(self):
        self.selenium.get('%s%s' % (self.live_server_url,
            reverse('foirequest-make_request',
                kwargs={'public_body': self.pb.slug})))
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_id('option-check_foi').is_displayed())
        self.selenium.find_element_by_id('option-check_foi').click()
        self.selenium.find_element_by_id('continue-foicheck').click()
        req_title = 'FoiRequest Number'
        self.selenium.find_element_by_id('id_subject').send_keys(req_title)
        self.selenium.find_element_by_id('id_body').send_keys('Documents describing something...')
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_elements_by_css_selector('#similar-requests li'))
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_id('review-button').is_displayed()
        )
        user_first_name = 'Peter'
        user_last_name = 'Parker'
        self.selenium.find_element_by_id('id_first_name')\
            .send_keys(user_first_name)
        self.selenium.find_element_by_id('id_last_name')\
            .send_keys(user_last_name)
        user_email = 'peter.parker@example.com'
        self.selenium.find_element_by_id('id_user_email')\
            .send_keys(user_email)
        self.selenium.find_element_by_id('id_terms').click()
        self.selenium.find_element_by_id('id_public').click()
        self.selenium.find_element_by_id('id_private').click()
        self.selenium.find_element_by_id('review-button').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('#review-text .highlight'))
        time.sleep(0.5)
        self.selenium.find_element_by_id('send-request-button').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('.heroine-unit'))
        new_user = User.objects.get(email=user_email)
        self.assertEqual(new_user.first_name, user_first_name)
        self.assertEqual(new_user.last_name, user_last_name)
        self.assertEqual(new_user.get_profile().private, True)
        req = FoiRequest.objects.get(user=new_user)
        self.assertEqual(req.title, req_title)
        self.assertEqual(req.public, False)
        self.assertEqual(req.public_body, self.pb)
        self.assertEqual(req.status, 'awaiting_user_confirmation')

    def test_make_logged_in_request(self):
        self.do_login()
        self.selenium.get('%s%s' % (self.live_server_url,
            reverse('foirequest-make_request')))
        search_pbs = self.selenium.find_element_by_id('id_public_body')
        search_pbs.send_keys(self.pb.name)
        self.selenium.find_element_by_class_name('search-public_bodies-submit').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('.search-results .result'))
        self.selenium.find_element_by_css_selector('.search-results .result label').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_id('option-check_foi').is_displayed())
        self.selenium.find_element_by_id('option-check_foi').click()
        self.selenium.find_element_by_id('continue-foicheck').click()
        req_title = 'FoiRequest Number'
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_id('id_body').is_displayed()
        )
        self.selenium.find_element_by_id('id_subject').send_keys(req_title)
        self.selenium.find_element_by_id('id_body').send_keys('Documents describing something...')
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_elements_by_css_selector('#similar-requests li'))
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_id('review-button').is_displayed()
        )
        self.selenium.find_element_by_id('review-button').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('#review-text .highlight'))
        time.sleep(0.5)
        self.selenium.find_element_by_id('send-request-button').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('#messages'))
        req = FoiRequest.objects.filter(user=self.user).order_by('-id')[0]
        self.assertIn(req.get_absolute_url(), self.selenium.current_url)
        self.assertEqual(req.title, req_title)
        self.assertEqual(req.public, True)
        self.assertEqual(req.public_body, self.pb)
        self.assertEqual(req.status, 'awaiting_response')
