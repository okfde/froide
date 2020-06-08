import os

from django.conf import settings
from django.db import connections
from django.core.management import call_command

from selenium import webdriver


def get_driver_options(driver_name, **kwargs):
    options = None
    if driver_name.startswith('chrome'):
        options = webdriver.ChromeOptions()
        if driver_name == 'chrome_headless':
            options.add_argument('headless')
            options.add_argument('disable-gpu')
            for key, val in kwargs.items():
                if val is not None:
                    options.add_argument('{key}={val}'.format(key=key, val=val))
                else:
                    options.add_argument('{key}'.format(key=key))
    elif driver_name.startswith('firefox'):
        options = webdriver.FirefoxOptions()
    return options


def get_selenium(**kwargs):
    driver_setting = getattr(settings, 'TEST_SELENIUM_DRIVER', 'firefox')

    driver_url = None
    if driver_setting.startswith('http'):
        driver_url, driver_name = driver_setting.split('#', 1)
    else:
        driver_name = driver_setting

    options = get_driver_options(driver_name, **kwargs)
    if driver_setting.startswith('http'):
        return webdriver.Remote(
            command_executor=driver_url,
            options=options
        )
    if driver_name.startswith('chrome'):
        driver_path = os.environ.get('CHROME_DRIVER_PATH', None)
        if driver_path is not None:
            return webdriver.Chrome(executable_path=driver_path, options=options)
        return webdriver.Chrome(options=options)
    else:
        return webdriver.Firefox(options=options)


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

    def _fixture_teardown(self):
        """
        This always cascades on truncate. From here:
        https://github.com/wagtail/wagtail/issues/1824#issuecomment-450575883
        Without it referencing foreign keys can't be truncated.
        Possibly only when used with fixtures.
        """
        # Allow TRUNCATE ... CASCADE and don't emit the post_migrate signal
        # when flushing only a subset of the apps
        for db_name in self._databases_names(include_mirrors=False):
            # Flush the database
            inhibit_post_migrate = (
                self.available_apps is not None or (  # Inhibit the post_migrate signal when using serialized
                    # rollback to avoid trying to recreate the serialized data.
                    self.serialized_rollback and
                    hasattr(connections[db_name], "_test_serialized_contents")
                )
            )
            call_command(
                "flush",
                verbosity=0,
                interactive=False,
                database=db_name,
                reset_sequences=False,
                # In the real TransactionTestCase this is conditionally set to False.
                allow_cascade=True,
                inhibit_post_migrate=inhibit_post_migrate,
            )
