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

__updated__ = '2018-08-05'


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
        self.assertEqual(settings.heating['on'], '/etc/thermod/switch-heating --on -j -s -q')
        self.assertEqual(settings.heating['off'], '/etc/thermod/switch-heating --off -j -s -q')
        self.assertEqual(settings.heating['status'], '/etc/thermod/switch-heating --status -j -s -q')
        self.assertEqual(settings.heating['pins'], [23])
        self.assertEqual(settings.heating['level'], 'l')
        
        self.assertEqual(settings.cooling['manager'], 'heating')
        self.assertEqual(settings.cooling['on'], '/etc/thermod/switch-cooling --on -j -s -q')
        self.assertEqual(settings.cooling['off'], '/etc/thermod/switch-cooling --off -j -s -q')
        self.assertEqual(settings.cooling['status'], '/etc/thermod/switch-cooling --status -j -s -q')
        self.assertEqual(settings.cooling['pins'], [24])
        self.assertEqual(settings.cooling['level'], 'l')
        
        self.assertEqual(settings.thermometer['script'], '/etc/thermod/get-temperature')
        self.assertEqual(settings.thermometer['scale'], 'c')
        self.assertEqual(settings.thermometer['similcheck'], True)
        self.assertEqual(settings.thermometer['simillen'], 12)
        self.assertEqual(settings.thermometer['simildelta'], 3.0)
        self.assertEqual(settings.thermometer['avgtask'], True)
        self.assertEqual(settings.thermometer['avgint'], 3)
        self.assertEqual(settings.thermometer['avgtime'], 6)
        self.assertEqual(settings.thermometer['avgskip'], 0.33)
        self.assertEqual(settings.thermometer['stddev'], 2.0)
        self.assertEqual(settings.thermometer['azchannels'], [0, 1, 2])
        self.assertEqual(settings.thermometer['w1devices'], ['28-000008e33449', '28-000008e3890d'])
        
        self.assertEqual(settings.host, 'localhost')
        self.assertEqual(settings.port, 4344)
        
        self.assertEqual(settings.email['server'], 'localhost')
        self.assertEqual(settings.email['credentials'], None)
        self.assertEqual(settings.email['sender'], 'Thermod <root@localhost>')
        self.assertEqual(settings.email['subject'], 'Thermod alert')
        self.assertEqual(settings.email['recipients'], ['Simone Rossetto <root@localhost>', 'other@localhost'])


if __name__ == "__main__":
    unittest.main()

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
