import re
import os
import logging

from django.conf import settings
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth import get_user_model
from django.core import mail

from selenium.webdriver.support.wait import WebDriverWait

from froide.foirequest.tests import factories
from froide.foirequest.models import FoiRequest
from froide.publicbody.models import PublicBody

User = get_user_model()


def get_selenium(**kwargs):
    driver = getattr(settings, 'TEST_SELENIUM_DRIVER', 'firefox')
    if driver in ('chrome', 'chrome_headless'):
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
        options = Options()
        if driver == 'chrome_headless':
            options.add_argument('headless')
            options.add_argument('disable-gpu')
            for key, val in kwargs.items():
                if val is not None:
                    options.add_argument('{key}={val}'.format(key=key, val=val))
                else:
                    options.add_argument('{key}'.format(key=key))
        driver_path = os.environ.get('CHROME_DRIVER_PATH', None)
        if driver_path is not None:
            return ChromeDriver(driver_path, options=options)
        return ChromeDriver(options=options)
    elif driver == 'phantomjs':
        from selenium.webdriver import PhantomJS
        return PhantomJS()
    else:
        from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxDriver
        return FirefoxDriver()


class JavaScriptException(Exception):
    pass


class CheckJSErrors(object):
    def __init__(self, driver):
        self.driver = driver

    def __enter__(self):
        self.driver.execute_script('''
            window.onerror=function(msg){
                document.getElementsByTagName('body')[0].setAttribute('jserror', msg);
            };
        ''')

    def __exit__(self, exc_type, exc_value, traceback):
        body = self.driver.find_elements_by_xpath('//body[@jserror]')
        if body:
            msg = body[0].get_attribute('jserror')
            raise JavaScriptException(msg)


class LiveTestMixin(object):
    ADDITIONAL_KWARGS = {}

    @classmethod
    def setUpClass(cls):
        cls.selenium = get_selenium(**cls.ADDITIONAL_KWARGS)
        cls.selenium.implicitly_wait(3)
        super(LiveTestMixin, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(LiveTestMixin, cls).tearDownClass()


class TestMakingRequest(LiveTestMixin, StaticLiveServerTestCase):

    def scrollTo(self, selector):
        # self.selenium.find_element_by_id(id).location_once_scrolled_into_view
        self.selenium.execute_script('window.scrollTo(0,0);'
                        'document.getElementById("%s").focus();' % selector)

    def setUp(self):
        factories.make_world()
        factories.rebuild_index()
        self.user = User.objects.get(username='dummy')
        self.pb = PublicBody.objects.all()[0]

    def go_to_make_request_url(self, pb=None):
        if pb is None:
            path = reverse('foirequest-make_request')
        else:
            path = reverse('foirequest-make_request', kwargs={
                'publicbody_ids': str(pb.pk)
            })
        self.selenium.get('%s%s' % (self.live_server_url, path))

    def do_login(self, navigate=True):
        if navigate:
            self.selenium.get('%s%s' % (self.live_server_url, reverse('account-login')))
        email_input = self.selenium.find_element_by_name('email')
        email_input.send_keys(self.user.email)
        password_input = self.selenium.find_element_by_name('password')
        password_input.send_keys('froide')
        self.selenium.find_element_by_xpath(
            '//form//button[contains(text(), "Log In")]').click()

    def test_make_not_logged_in_request(self):
        self.go_to_make_request_url()
        with CheckJSErrors(self.selenium):
            search_pbs = self.selenium.find_element_by_class_name('search-public_bodies')
            search_pbs.send_keys(self.pb.name)
            self.selenium.find_element_by_class_name('search-public_bodies-submit').click()
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_css_selector('.search-results .search-result'))
            self.selenium.find_element_by_css_selector('.search-results .search-result .btn').click()
            req_title = 'FoiRequest Number'
            self.selenium.find_element_by_name('subject').send_keys(req_title)
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_name('body').is_displayed())
            self.selenium.find_element_by_name('body').send_keys('Documents describing something...')
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_elements_by_css_selector('.similar-requests li'))
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_id('review-button').is_displayed()
            )
            self.selenium.find_element_by_name('first_name')\
                .send_keys('Peter')
            self.selenium.find_element_by_name('last_name')\
                .send_keys('Parker')
            user_email = 'peter.parker@example.com'
            self.selenium.find_element_by_name('user_email')\
                .send_keys(user_email)
            self.scrollTo('id_terms')
            self.selenium.find_element_by_name('terms').click()
            self.selenium.find_element_by_id('review-button').click()
            self.selenium.find_element_by_id('step-review')
            self.scrollTo('send-request-button')

        mail.outbox = []
        self.selenium.find_element_by_id('send-request-button').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('.heroine-unit'))
        new_user = User.objects.get(email=user_email)
        self.assertEqual(new_user.private, False)
        req = FoiRequest.objects.get(user=new_user)
        self.assertEqual(req.title, req_title)
        self.assertEqual(req.public, True)
        self.assertEqual(req.public_body, self.pb)
        self.assertEqual(req.status, 'awaiting_user_confirmation')

        message = mail.outbox[0]
        match = re.search(r'http://[^/]+(/.+)', message.body)
        activate_url = match.group(1)
        self.selenium.get('%s%s' % (self.live_server_url, activate_url))
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('#change-password-now'))
        self.assertIn('?new#change-password-now', self.selenium.current_url)
        req = FoiRequest.objects.get(user=new_user)
        self.assertEqual(req.status, 'awaiting_response')

    def test_make_not_logged_in_request_to_public_body(self):
        self.go_to_make_request_url(pb=self.pb)

        with CheckJSErrors(self.selenium):
            req_title = 'FoiRequest Number'
            self.selenium.find_element_by_name('subject').send_keys(req_title)
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_name('body').is_displayed())
            self.selenium.find_element_by_name('body').send_keys('Documents describing something...')
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_elements_by_css_selector('.similar-requests li'))
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_id('review-button').is_displayed()
            )
            user_first_name = 'Peter'
            user_last_name = 'Parker'
            self.selenium.find_element_by_name('first_name')\
                .send_keys(user_first_name)
            self.selenium.find_element_by_name('last_name')\
                .send_keys(user_last_name)
            user_email = 'peter.parker@example.com'
            self.selenium.find_element_by_name('user_email')\
                .send_keys(user_email)
            self.scrollTo('id_terms')
            self.selenium.find_element_by_name('terms').click()
            self.selenium.find_element_by_name('public').click()
            self.scrollTo('id_private')
            self.selenium.find_element_by_name('private').click()
            self.scrollTo('review-button')
            self.selenium.find_element_by_id('review-button').click()
            self.scrollTo('send-request-button')

        self.selenium.find_element_by_id('send-request-button').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('.heroine-unit'))
        new_user = User.objects.get(email=user_email)
        self.assertEqual(new_user.first_name, user_first_name)
        self.assertEqual(new_user.last_name, user_last_name)
        self.assertEqual(new_user.private, True)
        req = FoiRequest.objects.get(user=new_user)
        self.assertEqual(req.title, req_title)
        self.assertEqual(req.public, False)
        self.assertEqual(req.public_body, self.pb)
        self.assertEqual(req.status, 'awaiting_user_confirmation')

    def test_make_logged_in_request(self):
        self.do_login()
        self.go_to_make_request_url()

        with CheckJSErrors(self.selenium):
            search_pbs = self.selenium.find_element_by_class_name('search-public_bodies')
            search_pbs.send_keys(self.pb.name)
            self.selenium.find_element_by_class_name('search-public_bodies-submit').click()
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_css_selector('.search-results .search-result'))
            self.selenium.find_element_by_css_selector('.search-results .search-result .btn').click()
            req_title = 'FoiRequest Number'
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_name('body').is_displayed()
            )
            self.selenium.find_element_by_name('subject').send_keys(req_title)
            self.scrollTo('full_text_checkbox')
            self.selenium.find_element_by_name('full_text_checkbox').click()
            self.scrollTo('id_body')
            self.selenium.find_element_by_name('body').clear()
            body_text = 'Documents describing & something...'
            self.selenium.find_element_by_name('body').send_keys(body_text)
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_elements_by_css_selector('.similar-requests li'))
            self.scrollTo('review-button')
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_id('review-button').is_displayed()
            )
            self.selenium.find_element_by_id('review-button').click()
            self.scrollTo('send-request-button')

        WebDriverWait(self.selenium, 10).until(
            lambda driver: self.selenium.find_element_by_id('send-request-button').is_displayed())
        self.selenium.find_element_by_id('send-request-button').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('#messages'))
        req = FoiRequest.objects.filter(user=self.user).order_by('-id')[0]
        self.assertIn(req.get_absolute_url(), self.selenium.current_url)
        self.assertEqual(req.title, req_title)
        self.assertEqual(req.description, body_text)
        self.assertTrue(req.messages[0].plaintext.startswith(body_text))
        self.assertEqual(req.public, True)
        self.assertEqual(req.public_body, self.pb)
        self.assertEqual(req.status, 'awaiting_response')

    def test_make_request_logged_out_with_existing_account(self):
        self.go_to_make_request_url(pb=self.pb)
        with CheckJSErrors(self.selenium):
            req_title = 'FoiRequest Number'
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_name('body').is_displayed()
            )
            self.selenium.find_element_by_name('subject').send_keys(req_title)
            self.selenium.find_element_by_name('body').send_keys('Documents describing something...')
            user_first_name = self.user.first_name
            user_last_name = self.user.last_name
            self.selenium.find_element_by_name('first_name')\
                .send_keys(user_first_name)
            self.selenium.find_element_by_name('last_name')\
                .send_keys(user_last_name)
            self.selenium.find_element_by_name('user_email').send_keys(self.user.email)
            self.scrollTo('id_terms')
            self.selenium.find_element_by_name('terms').click()
            self.selenium.find_element_by_name('public').click()
            self.scrollTo('id_private')
            self.selenium.find_element_by_name('private').click()

            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_elements_by_css_selector('.similar-requests li'))
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_id('review-button').is_displayed()
            )
            self.scrollTo('review-button')
            self.selenium.find_element_by_id('review-button').click()
            self.scrollTo('send-request-button')

        WebDriverWait(self.selenium, 10).until(
            lambda driver: self.selenium.find_element_by_id('send-request-button').is_displayed())
        self.selenium.find_element_by_id('send-request-button').click()
        main_window_handle = self.selenium.current_window_handle
        login_link = '#simple-login-link'
        with CheckJSErrors(self.selenium):
            WebDriverWait(self.selenium, 10).until(
                lambda driver: self.selenium.find_element_by_css_selector(login_link)
            )
            self.scrollTo(login_link[1:])
            WebDriverWait(self.selenium, 10).until(
                lambda driver: self.selenium.find_element_by_css_selector(login_link).is_displayed())
            self.selenium.find_element_by_css_selector(login_link).click()

        popup_handle = [wh for wh in self.selenium.window_handles if wh != main_window_handle][0]
        self.selenium.switch_to.window(popup_handle)

        with CheckJSErrors(self.selenium):
            password_input = self.selenium.find_element_by_name('password')
            password_input.send_keys('froide')

        self.selenium.find_element_by_xpath(
            '//form//button[contains(text(), "Log In")]').click()
        self.selenium.switch_to.window(main_window_handle)

        with CheckJSErrors(self.selenium):
            self.selenium.find_element_by_id('review-button').click()
            self.scrollTo('send-request-button')

        WebDriverWait(self.selenium, 10).until(
            lambda driver: self.selenium.find_element_by_id('send-request-button').is_displayed())
        self.selenium.find_element_by_id('send-request-button').click()

        req = FoiRequest.objects.filter(user=self.user).order_by('-id')[0]
        self.assertIn(req.get_absolute_url(), self.selenium.current_url)
        self.assertEqual(req.title, req_title)
        self.assertEqual(req.public, False)
        self.assertEqual(req.public_body, self.pb)


class MenuTest(LiveTestMixin, StaticLiveServerTestCase):
    SCREEN_SIZE = (400, 800)
    ADDITIONAL_KWARGS = {'window-size': '%s,%s' % SCREEN_SIZE}

    def test_collapsed_menu(self):
        try:
            self.selenium.set_window_size(*self.SCREEN_SIZE)
        except Exception as e:
            logging.exception(e)
        logging.warning('Window size: %s', self.selenium.get_window_size())
        with CheckJSErrors(self.selenium):
            self.selenium.get('%s%s' % (self.live_server_url,
                reverse('index')))
            search_form = self.selenium.find_element_by_css_selector('.navbar form[role=search]')
            self.assertFalse(search_form.is_displayed())
            self.selenium.find_element_by_css_selector('.navbar-toggler').click()
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_css_selector('.navbar form[role=search]').is_displayed()
            )
