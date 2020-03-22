#!/usr/bin/python
import os
from setuptools import setup
from etsy import __version__, __author__, __email__, __license__

this_dir = os.path.realpath(os.path.dirname(__file__))
long_description = open(os.path.join(this_dir, 'README.md'), 'r').read()

setup(
    name = 'etsy',
    version = __version__,
    author = __author__,
    author_email = __email__,
    description = 'Python access to the Etsy V2 API',
    license = __license__,
    keywords = 'etsy api handmade',
    packages = ['etsy'],
    long_description = long_description,
    install_requires=['requests-oauthlib', 'requests']
)
