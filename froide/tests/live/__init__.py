import os

from django.conf import settings


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

    def scrollTo(self, selector):
        # self.selenium.find_element_by_id(id).location_once_scrolled_into_view
        self.selenium.execute_script('window.scrollTo(0,0);'
                        'document.getElementById("%s").focus();' % selector)
