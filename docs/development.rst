Development
===========

Run tests
---------

Froide has a test suite. You have to install the test dependencies first::

    pip install -r requirements-test.txt

The default test configuration requires a running elasticsearch instance.
You either have to install elasticsearch or change the configuration to
another search engine.

Then you can run the tests::

    make test

This also does test coverage analysis that you can then
find at `htmlcov/index.html`.


Build docs
----------

The docs can be build with Sphinx but first you must install the theme.
Excecute these commands from the top level of the froide directory::

  git submodule init
  git submodule update

Then change into the `docs` directory and type::

  make html

The documentation will be build and you can find the resulting html in `docs/_build/html`.
