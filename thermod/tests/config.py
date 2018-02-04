# -*- coding: utf-8 -*-
"""Test suite for `thermod.config` module.

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

import os
import unittest
import thermod.config as cnf

__updated__ = '2017-12-03'

# TODO write more tests for specific settings and possible errors


class TestHeating(unittest.TestCase):
    """Test cases for `thermod.config` module."""

    def setUp(self):
        pass
    
    def tearDown(self):
        pass
    
    def test_parsing_config(self):
        (cfg, err) = cnf.read_config_file(os.path.join('etc', cnf.MAIN_CONFIG_FILENAME))
        self.assertEqual(err, 0)
        
        settings = cnf.parse_main_settings(cfg)
        self.assertEqual(settings.enabled, False)
        self.assertEqual(settings.debug, False)
        self.assertEqual(settings.interval, 30)
        self.assertEqual(settings.mode, 2)
        self.assertEqual(settings.heating['manager'], 'scripts')
        self.assertEqual(settings.thermometer['scale'], 'c')
        self.assertEqual(settings.host, 'localhost')
        self.assertEqual(settings.port, 4344)


if __name__ == "__main__":
    unittest.main()

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
