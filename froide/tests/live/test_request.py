import re

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth import get_user_model
from django.core import mail

from selenium.webdriver.support.wait import WebDriverWait

from froide.foirequest.tests import factories
from froide.foirequest.models import FoiRequest
from froide.publicbody.models import PublicBody

User = get_user_model()


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


class JavaScriptException(Exception):
    pass


class CheckJSErrors(object):
    def __init__(self, driver):
        self.driver = driver

    def __enter__(self):
        self.driver.execute_script('''
            window.onerror=function(msg){
                $('body').attr('jserror', msg);
            };
        ''')

    def __exit__(self, exc_type, exc_value, traceback):
        body = self.driver.find_elements_by_xpath('//body[@jserror]')
        if body:
            msg = body[0].get_attribute('jserror')
            raise JavaScriptException(msg)


class TestMakingRequest(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        cls.selenium = get_selenium()
        cls.selenium.implicitly_wait(3)
        super(TestMakingRequest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(TestMakingRequest, cls).tearDownClass()

    def scrollTo(self, id=None, klass=None):
        if id is not None:
            self.selenium.find_element_by_id(id).location_once_scrolled_into_view
            selector = '#' + id
        if klass is not None:
            self.selenium.find_element_by_class_name(klass).location_once_scrolled_into_view
            selector = '.' + klass
        self.selenium.execute_script("window.scrollTo(0,0);$('%s').focus();" % selector)

    def setUp(self):
        factories.make_world()
        factories.rebuild_index()
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
            '//form//button[contains(text(), "Log In")]').click()

    def test_make_not_logged_in_request(self):
        self.selenium.get('%s%s' % (self.live_server_url,
            reverse('foirequest-make_request')))
        with CheckJSErrors(self.selenium):
            search_pbs = self.selenium.find_element_by_id('id_public_body')
            search_pbs.send_keys(self.pb.name)
            self.selenium.find_element_by_class_name('search-public_bodies-submit').click()
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_css_selector('.search-results .search-result'))
            self.selenium.find_element_by_css_selector('.search-results .search-result label').click()
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_id('option-check_foi').is_displayed())
            self.selenium.find_element_by_id('option-check_foi').click()
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_id('continue-foicheck'))
            self.selenium.find_element_by_id('continue-foicheck').click()
            req_title = 'FoiRequest Number'
            self.selenium.find_element_by_id('id_subject').send_keys(req_title)
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_id('id_body').is_displayed())
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
            self.selenium.find_element_by_id('step-review')
            WebDriverWait(self.selenium, 10).until(
                lambda driver: 'in' in self.selenium.find_element_by_id('step-review').get_attribute('class'))
            self.scrollTo(id='send-request-button')

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
        match = re.search('http://[^/]+(/.+)', message.body)
        activate_url = match.group(1)
        self.selenium.get('%s%s' % (self.live_server_url, activate_url))
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('#change-password-now'))
        self.assertIn('?new#change-password-now', self.selenium.current_url)
        req = FoiRequest.objects.get(user=new_user)
        self.assertEqual(req.status, 'awaiting_response')

    def test_make_not_logged_in_request_to_public_body(self):
        self.selenium.get('%s%s' % (self.live_server_url,
            reverse('foirequest-make_request',
                kwargs={'public_body': self.pb.slug})))

        with CheckJSErrors(self.selenium):
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_id('option-check_foi').is_displayed())
            self.selenium.find_element_by_id('option-check_foi').click()
            self.selenium.find_element_by_id('continue-foicheck').click()
            req_title = 'FoiRequest Number'
            self.selenium.find_element_by_id('id_subject').send_keys(req_title)
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_id('id_body').is_displayed())
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
            WebDriverWait(self.selenium, 10).until(
                lambda driver: 'in' in self.selenium.find_element_by_id('step-review').get_attribute('class'))
            self.scrollTo(id='send-request-button')

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
        self.selenium.get('%s%s' % (self.live_server_url,
            reverse('foirequest-make_request')))
        with CheckJSErrors(self.selenium):
            search_pbs = self.selenium.find_element_by_id('id_public_body')
            search_pbs.send_keys(self.pb.name)
            self.selenium.find_element_by_class_name('search-public_bodies-submit').click()
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_css_selector('.search-results .search-result'))
            self.selenium.find_element_by_css_selector('.search-results .search-result label').click()
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
            WebDriverWait(self.selenium, 10).until(
                lambda driver: 'in' in self.selenium.find_element_by_id('step-review').get_attribute('class'))
            self.scrollTo(id='send-request-button')

        WebDriverWait(self.selenium, 10).until(
            lambda driver: self.selenium.find_element_by_id('send-request-button').is_displayed())
        self.selenium.find_element_by_id('send-request-button').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('#messages'))
        req = FoiRequest.objects.filter(user=self.user).order_by('-id')[0]
        self.assertIn(req.get_absolute_url(), self.selenium.current_url)
        self.assertEqual(req.title, req_title)
        self.assertEqual(req.public, True)
        self.assertEqual(req.public_body, self.pb)
        self.assertEqual(req.status, 'awaiting_response')

    def test_make_logged_in_request_no_pb_yet(self):
        self.do_login()
        self.selenium.get('%s%s' % (self.live_server_url,
            reverse('foirequest-make_request')))
        with CheckJSErrors(self.selenium):
            self.selenium.find_element_by_id('option-emptypublicbody').click()
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
            WebDriverWait(self.selenium, 10).until(
                lambda driver: 'in' in self.selenium.find_element_by_id('step-review').get_attribute('class'))
            self.scrollTo(id='send-request-button')

        WebDriverWait(self.selenium, 10).until(
            lambda driver: self.selenium.find_element_by_id('send-request-button').is_displayed())
        self.selenium.find_element_by_id('send-request-button').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('#messages'))
        req = FoiRequest.objects.filter(user=self.user).order_by('-id')[0]
        self.assertIn(req.get_absolute_url(), self.selenium.current_url)
        self.assertEqual(req.title, req_title)
        self.assertEqual(req.public, True)
        self.assertTrue(req.public_body is None)
        self.assertEqual(req.status, 'publicbody_needed')

    def test_make_request_logged_out_with_existing_account(self):
        self.selenium.get('%s%s' % (self.live_server_url,
            reverse('foirequest-make_request')))
        with CheckJSErrors(self.selenium):
            self.selenium.find_element_by_id('option-emptypublicbody').click()
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
            user_first_name = self.user.first_name
            user_last_name = self.user.last_name
            self.selenium.find_element_by_id('id_first_name')\
                .send_keys(user_first_name)
            self.selenium.find_element_by_id('id_last_name')\
                .send_keys(user_last_name)
            self.selenium.find_element_by_id("id_user_email").send_keys(self.user.email)
            self.selenium.find_element_by_id('id_terms').click()
            self.selenium.find_element_by_id('id_public').click()
            self.selenium.find_element_by_id('id_private').click()

            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_elements_by_css_selector('#similar-requests li'))
            WebDriverWait(self.selenium, 5).until(
                lambda driver: driver.find_element_by_id('review-button').is_displayed()
            )
            self.selenium.find_element_by_id('review-button').click()
            WebDriverWait(self.selenium, 10).until(
                lambda driver: 'in' in self.selenium.find_element_by_id('step-review').get_attribute('class'))
            self.scrollTo(id='send-request-button')

        WebDriverWait(self.selenium, 10).until(
            lambda driver: self.selenium.find_element_by_id('send-request-button').is_displayed())
        self.selenium.find_element_by_id('send-request-button').click()
        main_window_handle = self.selenium.current_window_handle
        login_link = '//div[@class="user_data_form"]//ul[@class="errorlist"]//a'
        with CheckJSErrors(self.selenium):
            WebDriverWait(self.selenium, 10).until(
                lambda driver: self.selenium.find_element_by_xpath(login_link)
            )
            self.scrollTo(klass='target-small')
            WebDriverWait(self.selenium, 10).until(
                lambda driver: self.selenium.find_element_by_xpath(login_link).is_displayed())
            self.selenium.find_element_by_xpath(login_link).click()

        popup_handle = [wh for wh in self.selenium.window_handles if wh != main_window_handle][0]
        self.selenium.switch_to_window(popup_handle)

        with CheckJSErrors(self.selenium):
            password_input = self.selenium.find_element_by_id("id_password")
            password_input.send_keys('froide')

        self.selenium.find_element_by_xpath(
            '//form//button[contains(text(), "Log In")]').click()
        self.selenium.switch_to_window(main_window_handle)

        with CheckJSErrors(self.selenium):
            self.selenium.find_element_by_id('review-button').click()
            WebDriverWait(self.selenium, 10).until(
                lambda driver: 'in' in self.selenium.find_element_by_id('step-review').get_attribute('class'))
            self.scrollTo(id='send-request-button')

        WebDriverWait(self.selenium, 10).until(
            lambda driver: self.selenium.find_element_by_id('send-request-button').is_displayed())
        self.selenium.find_element_by_id('send-request-button').click()

        req = FoiRequest.objects.filter(user=self.user).order_by('-id')[0]
        self.assertIn(req.get_absolute_url(), self.selenium.current_url)
        self.assertEqual(req.title, req_title)
        self.assertEqual(req.public, False)
        self.assertTrue(req.public_body is None)
        self.assertEqual(req.status, 'publicbody_needed')

    def test_collapsed_menu(self):
        self.selenium.set_window_size(600, 800)
        self.selenium.get('%s%s' % (self.live_server_url,
            reverse('index')))
        self.selenium.find_element_by_css_selector('.navbar-toggle').click()
        WebDriverWait(self.selenium, 5).until(
            lambda driver: driver.find_element_by_css_selector('.navbar-form').is_displayed()
        )
