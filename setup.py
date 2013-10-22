import codecs
from os import path
from setuptools import setup


def read(*parts):
    file_path = path.join(path.dirname(__file__), *parts)
    return codecs.open(file_path, encoding='utf-8').read()


setup(
    name="froide",
    version='4.0.0-alpha',
    url='https://github.com/stefanw/froide',
    license='MIT',
    description="German Freedom of Information Portal",
    long_description=read('README.md'),
    author='Stefan Wehrmeyer',
    author_email='mail@stefanwehrmeyer.com',
    packages=[
        'froide',
    ],
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
