# -*- coding: utf-8 -*-
"""Setup script for Thermod daemon.

Copyright (C) 2018 Simone Rossetto <simros85@gmail.com>

This file is part of Thermod.

Thermod is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Thermod is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Thermod.  If not, see <http://www.gnu.org/licenses/>.
"""

from setuptools import setup

def get_version():
    main_ns = {}
    with open('thermod/version.py','r') as version_file:
        exec(version_file.read(), main_ns)
    return main_ns['__version__']

setup(name='thermod',
      version=get_version(),
      description='Programmable thermostat daemon for smart-heating automation.',
      long_description='Programmable thermostat daemon for smart-heating automation.',
      author='Simone Rossetto',
      author_email='simros85@gmail.com',
      url='https://github.com/droscy/thermod',
      license = 'GPL-3.0+',
      packages=['thermod'],
      scripts=['bin/thermod'],
      install_requires=['jsonschema >= 2.3.0',
                        'async_timeout >= 1.3.0',
                        'aiohttp >= 3.0.1',
                        'numpy >= 1.8.0'],
      test_suite='nose.collector',
      tests_require=['nose >= 1.3.4'],
)

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
