from playwright.sync_api import sync_playwright


class JavaScriptException(Exception):
    pass


class CheckJSErrors(object):
    def __init__(self, driver):
        self.driver = driver

    def __enter__(self):
        self.driver.execute_script(
            """
            window.onerror=function(msg){
                document.getElementsByTagName('body')[0].setAttribute('jserror', msg);
            };
        """
        )

    def __exit__(self, exc_type, exc_value, traceback):
        body = self.driver.find_elements_by_xpath("//body[@jserror]")
        if body:
            msg = body[0].get_attribute("jserror")
            raise JavaScriptException(msg)


class LiveTestMixin(object):
    @classmethod
    def setUpClass(cls):
        super(LiveTestMixin, cls).setUpClass()
        cls.playwright = sync_playwright()
        cls.browser = cls.playwright.chromium.launch(headless=False)

    @classmethod
    def tearDownClass(cls):
        super(LiveTestMixin, cls).tearDownClass()
        cls.browser.close()
        cls.playwright.stop()
