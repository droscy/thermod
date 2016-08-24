# -*- coding: utf-8 -*-

from setuptools import setup

def get_version():
    main_ns = {}
    with open('thermod/version.py','r') as version_file:
        exec(version_file.read(), main_ns)
    return main_ns['__version__']

setup(name='thermod',
      version=get_version(),
      description='Programmable thermostat daemon for smart-heating automation.',
      long_description='TODO',
      author='Simone Rossetto',
      author_email='simros85@gmail.com',
      url='TODO',
      license = 'GPL-3.0+',
      packages=['thermod'],
      scripts=['bin/thermod'],
      install_requires=['python-daemon >= 2.0.5',
                        'jsonschema >= 2.3.0',
                        'requests >= 2.4.3'],
      test_suite='nose.collector',
      tests_require=['nose >= 1.3.4', 'requests >= 2.4.3'],
)

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab