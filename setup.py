#!/usr/bin/env python

import codecs
import re
import os

from setuptools import setup, find_packages


def read(*parts):
    filename = os.path.join(os.path.dirname(__file__), *parts)
    with codecs.open(filename, encoding='utf-8') as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="froide",
    version=find_version("froide", "__init__.py"),
    url='https://github.com/stefanw/froide',
    license='MIT',
    description="German Freedom of Information Portal",
    long_description=read('README.md'),
    author='Stefan Wehrmeyer',
    author_email='mail@stefanwehrmeyer.com',
    packages=find_packages(),
    install_requires=[
        'Django',
        'Markdown',
        'celery',
        'django-celery',
        'django-haystack',
        'django-taggit',
        'pytz',
        'requests',
        'django-floppyforms',
        'django_overextends',
        'python-magic',
        'django-tastypie',
        'python-mimeparse',
        'unicodecsv',
        'django-configurations',
        'django-storages',
        'dj-database-url',
        'django-cache-url',
        'django_compressor',
    ],
    include_package_data=True,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet :: WWW/HTTP'
    ]
)
