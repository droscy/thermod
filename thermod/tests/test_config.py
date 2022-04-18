# -*- coding: utf-8 -*-
"""Test suite for `thermod.config` module.

Copyright (C) 2018-2022 Simone Rossetto <simros85@gmail.com>

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
import thermod.common as common

__updated__ = '2021-04-08'


# TODO write more tests for specific settings and possible errors
class TestHeating(unittest.TestCase):
    """Test cases for `thermod.config` module."""

    def setUp(self):
        pass
    
    def tearDown(self):
        pass
    
    def test_parsing_config(self):
        (cfg, err) = cnf.read_config_file(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'etc', cnf.MAIN_CONFIG_FILENAME)))
        self.assertEqual(err, 0)
        
        (settings, error_code) = cnf.parse_main_settings(cfg)
        self.assertEqual(error_code, common.RET_CODE_OK)
        self.assertEqual(settings.enabled, False)
        self.assertEqual(settings.debug, False)
        self.assertEqual(settings.interval, 30)
        self.assertEqual(settings.sleep_on_error, 30)
        self.assertEqual(settings.inertia, 1)
        self.assertEqual(settings.scale, common.DEGREE_CELSIUS)
        
        self.assertEqual(settings.heating['manager'], 'scripts')
        self.assertEqual(settings.heating['on'], '/etc/thermod/switch-heating --on -j -s -q')
        self.assertEqual(settings.heating['off'], '/etc/thermod/switch-heating --off -j -s -q')
        self.assertEqual(settings.heating['status'], '/etc/thermod/switch-heating --status -j -s -q')
        self.assertEqual(settings.heating['pins'], [23])
        self.assertEqual(settings.heating['level'], 'l')
        
        self.assertEqual(settings.thermometer['thermometer'], '/etc/thermod/get-temperature')
        self.assertEqual(settings.thermometer['scale'], 'c')
        self.assertEqual(settings.thermometer['similcheck'], True)
        self.assertEqual(settings.thermometer['simillen'], 12)
        self.assertEqual(settings.thermometer['simildelta'], 3.0)
        self.assertEqual(settings.thermometer['avgtask'], True)
        self.assertEqual(settings.thermometer['avgint'], 3)
        self.assertEqual(settings.thermometer['avgtime'], 6)
        self.assertEqual(settings.thermometer['avgskip'], 0.33)
        self.assertEqual(settings.thermometer['az']['channels'], [0, 1, 2])
        self.assertEqual(settings.thermometer['az']['stddev'], 2.0)
        self.assertEqual(settings.thermometer['w1']['devices'], ['28-000008e33449', '28-000008e3890d'])
        self.assertEqual(settings.thermometer['w1']['stddev'], 2.0)
        
        self.assertEqual(settings.host, 'localhost')
        self.assertEqual(settings.port, 4344)
        
        self.assertEqual(settings.email['server'], 'localhost')
        self.assertEqual(settings.email['credentials'], None)
        self.assertEqual(settings.email['sender'], 'Thermod <root@localhost>')
        self.assertEqual(settings.email['subject'], 'Thermod alert')
        self.assertEqual(settings.email['recipients'], ['Simone Rossetto <root@localhost>', 'other@localhost'])
        self.assertEqual(settings.email['level'], 'warning')


if __name__ == "__main__":
    unittest.main()

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
