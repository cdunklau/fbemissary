import os

from setuptools import setup, find_packages


requires = [
    'aiohttp',
    'attrs',
]
classifiers = [
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3 :: Only',
    'Framework :: AsyncIO',
    'Topic :: Internet',
    'Topic :: Communications :: Chat',
    'License :: OSI Approved :: Apache Software License',
    'Development Status :: 2 - Pre-Alpha',
]

description = (
    'A bot framework for the Facebook Messenger platform, '
    'built on asyncio and aiohttp'
)

setup(
    name='fbemissary',
    version='0.0.1',
    description=description,
    author='Colin Dunklau',
    author_email='colin.dunklau@gmail.com',
    url='https://github.com/cdunklau/fbemissary',
    classifiers=classifiers,
    packages=find_packages(include=['fbemissary', 'fbemissary.tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
)
