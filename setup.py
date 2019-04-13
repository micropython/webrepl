#!/usr/bin/env python

from setuptools import setup, find_packages


setup(name='webrepl_cli',
      version='0.20190413',
      description='WebREPL client for MicroPython',
      author=u'MicroPython Team',
      author_email='contact@micropython.org',
      url='https://github.com/micropython/webrepl',
      scripts=["webrepl_cli.py"],
      license="MIT",
      keywords="micropython webrepl esp8266 esp32",
      packages=find_packages(),
      install_requires=[],
      package_data={})
