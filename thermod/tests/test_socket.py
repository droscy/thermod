# -*- coding: utf-8 -*-
"""Test suite for `thermod.socket` module.

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
import copy
import logging
import tempfile
import unittest
import asyncio
import aiohttp

from thermod import socket, timetable, common
from thermod.timetable import TimeTable
from thermod.heating import BaseHeating
from thermod.socket import ControlSocket
from thermod.thermometer import FakeThermometer
from thermod.tests.test_timetable import fill_timetable

__updated__ = '2020-12-06'
__url_settings__ = 'http://localhost:4345/settings'
__url_heating__ = 'http://localhost:4345/status'


class TestSocket(unittest.TestCase):
    """Test cases for `thermod.socket` module."""
    
    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.lock = asyncio.Condition()
        
        self.timetable = TimeTable()
        fill_timetable(self.timetable)
        self.timetable.filepath = os.path.join(tempfile.gettempdir(), 'timetable.json')
        self.timetable.save()
        
        self.heating = BaseHeating()
        self.thermometer = FakeThermometer()
        
        self.socket = ControlSocket(self.timetable,
                                    self.heating,
                                    self.thermometer,
                                    'localhost',
                                    4345,  # using different port to run test while real thermod is running
                                    self.lock)
        self.loop.run_until_complete(self.socket.start())
    
    
    def tearDown(self):
        self.loop.run_until_complete(self.socket.stop())
        os.remove(self.timetable.filepath)
    
    
    def test_get_settings(self):
        async def this_test():
            async with aiohttp.ClientSession() as session:
                # wrong url
                async with session.get('http://localhost:4345/wrong') as wrong:
                    self.assertEqual(wrong.status, 404)
                
                # right url
                async with session.get(__url_settings__) as r:
                    self.assertEqual(r.status, 200)
                    settings = await r.json()
                
                # check returned settings
                tt = TimeTable()
                tt.__setstate__(settings)
                self.assertEqual(self.timetable, tt)
        
        self.loop.run_until_complete(this_test())
    
    
    def test_get_heating(self):
        async def this_test():
            async with aiohttp.ClientSession() as session:
                # wrong url
                async with session.get('http://localhost:4345/wrong') as wrong:
                    self.assertEqual(wrong.status, 404)
                
                # right url
                async with session.get(__url_heating__) as r:
                    self.assertEqual(r.status, 200)
                    heating = await r.json()
                
                # check returned heating informations
                self.assertEqual(heating['mode'], self.timetable.mode)
                self.assertEqual(heating['status'], await self.heating.status)
                self.assertAlmostEqual(heating['current_temperature'], await self.thermometer.temperature, delta=0.1)
                self.assertEqual(heating['target_temperature'], self.timetable.target_temperature())
    
        self.loop.run_until_complete(this_test())
    
    
    def test_post_wrong_messages(self):
        async def this_test():
            async with aiohttp.ClientSession() as session:
                # wrong url
                async with session.post('http://localhost:4345/wrong', data={}) as wrong:
                    self.assertEqual(wrong.status, 404)
                
                # wrong value for status
                async with session.post(__url_settings__, data={socket.REQ_SETTINGS_MODE: 'invalid'}) as wrong:
                    self.assertEqual(wrong.status, 400)
                
                # wrong value (greater then max allowed)
                async with session.post(__url_settings__, data={socket.REQ_SETTINGS_DIFFERENTIAL: 1.1}) as wrong:
                    self.assertEqual(wrong.status, 400)
                
                # wrong value (invalid)
                async with session.post(__url_settings__, data={socket.REQ_SETTINGS_HVAC_MODE: 'invalid'}) as wrong:
                    self.assertEqual(wrong.status, 400)
                
                # wrong JSON data for settings
                settings = self.timetable.__getstate__()
                settings[timetable.JSON_TEMPERATURES][timetable.JSON_TMAX_STR] = 'inf'
                async with session.post(__url_settings__, data={socket.REQ_SETTINGS_ALL: settings}) as wrong:
                    self.assertEqual(wrong.status, 400)
                
                # invalid JSON syntax for settings
                settings = self.timetable.settings()
                async with session.post(__url_settings__, data={socket.REQ_SETTINGS_ALL: settings[0:30]}) as wrong:
                    self.assertEqual(wrong.status, 400)
                
                # check original paramethers
                self.assertAlmostEqual(self.timetable.differential, 0.5, delta=0.01)
                self.assertAlmostEqual(self.timetable.tmax, 21, delta=0.01)
        
        self.loop.run_until_complete(this_test())
    
    
    def test_post_right_messages(self):
        async def this_test():
            async with aiohttp.ClientSession() as session:
                # single settings
                async with session.post(__url_settings__, data={socket.REQ_SETTINGS_MODE: timetable.JSON_MODE_OFF}) as p:
                    self.assertEqual(p.status, 200)
                    self.assertEqual(self.timetable.mode, timetable.JSON_MODE_OFF)
                
                # multiple settings
                async with session.post(__url_settings__,
                                        data={socket.REQ_SETTINGS_MODE: timetable.JSON_MODE_TMAX,
                                              socket.REQ_SETTINGS_TMAX: 32.3,
                                              socket.REQ_SETTINGS_HVAC_MODE: common.HVAC_COOLING}) as q:
                    
                    self.assertEqual(q.status, 200)
                    self.assertEqual(self.timetable.mode, timetable.JSON_MODE_TMAX)
                    self.assertAlmostEqual(self.timetable.tmax, 32.3, delta=0.01)
                
                # some days
                old_set = self.timetable.__getstate__()
                friday = old_set[timetable.JSON_TIMETABLE][timetable.json_get_day_name(5)]
                sunday = old_set[timetable.JSON_TIMETABLE][timetable.json_get_day_name(7)]
                
                friday['h12'][0] = 44
                friday['h15'][1] = 45
                sunday['h06'][2] = 46
                sunday['h07'][3] = 47
                
                # all settings
                tt2 = copy.deepcopy(self.timetable)
                tt2.mode = timetable.JSON_MODE_TMAX
                tt2.update('thursday', 4, 1, 36.5)
                
                self.assertNotEqual(self.timetable, tt2)  # different before update
                
                async with session.post(__url_settings__, data={socket.REQ_SETTINGS_ALL: tt2.settings()}) as s:
                    self.assertEqual(s.status, 200)
        
                self.assertEqual(self.timetable, tt2)  # equal after update
        
        self.loop.run_until_complete(this_test())
    
    
    def test_unsupported_http_methods(self):
        async def this_test():
            async with aiohttp.ClientSession() as session:
                async with session.patch(__url_settings__, data={}) as pa:
                    self.assertEqual(pa.status, 501)
                
                async with session.put(__url_settings__, data={}) as pu:
                    self.assertEqual(pu.status, 501)
                
                async with session.delete(__url_heating__) as de:
                    self.assertEqual(de.status, 501)
        
        self.loop.run_until_complete(this_test())


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL)
    unittest.main(warnings='ignore')

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
