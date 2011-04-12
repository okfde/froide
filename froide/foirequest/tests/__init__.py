import unittest
import test_mail
import test_request
import test_web

__tests__ = [test_mail, test_request, test_web]  

def suite():
    suite = unittest.TestSuite()
    tests = []                           
    for test in __tests__:
        tl = unittest.TestLoader().loadTestsFromModule(test)
        tests += tl._tests
    suite._tests = tests
    return suite

