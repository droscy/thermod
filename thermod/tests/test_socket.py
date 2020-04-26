# -*- coding: utf-8 -*-
"""Test suite for `thermod.socket` module.

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
import copy
import logging
import tempfile
import unittest
import requests
import threading
import asyncio
import time

import thermod.socket as socket
from thermod import TimeTable, BaseHeating, ControlSocket, utils, common, timetable
from thermod.cooling import BaseCooling
from thermod.thermometer import FakeThermometer
from thermod.tests.test_timetable import fill_timetable

__updated__ = '2018-08-06'
__url_settings__ = 'http://localhost:4344/settings'
__url_heating__ = 'http://localhost:4344/status'


class SocketThread(threading.Thread):
    """Thread to execut the socket and its loop"""
    
    def __init__(self, timetable, heating, cooling, thermometer, lock):
        super().__init__()
        self.timetable = timetable
        self.heating = heating
        self.cooling = cooling
        self.thermometer = thermometer
        self.lock = lock
    
    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.socket = ControlSocket(self.timetable,
                                    self.heating,
                                    self.cooling,
                                    self.thermometer,
                                    common.SOCKET_DEFAULT_HOST,
                                    common.SOCKET_DEFAULT_PORT,
                                    self.lock,
                                    self.loop)
        self.socket.start()
        
        try:
            self.loop.run_forever()
        
        finally:
            self.socket.stop()
            self.loop.close()
    
    def stop(self):
        self.loop.stop()

class TestSocket(unittest.TestCase):
    """Test cases for `thermod.socket` module."""
    
    def setUp(self):
        self.lock = asyncio.Condition()
        
        self.timetable = TimeTable()
        fill_timetable(self.timetable)
        self.timetable.filepath = os.path.join(tempfile.gettempdir(), 'timetable.json')
        self.timetable.save()
        
        self.heating = BaseHeating()
        self.cooling = BaseCooling()
        self.thermometer = FakeThermometer()
        
        self.socket = SocketThread(self.timetable, self.heating, self.cooling, self.thermometer, self.lock)
        self.socket.start()
        time.sleep(1)
    
    
    def tearDown(self):
        self.socket.stop()
        self.socket.join()
        os.remove(self.timetable.filepath)
    
    
    def test_get_settings(self):
        # wrong url
        wrong = requests.get('http://localhost:4344/wrong')
        self.assertEqual(wrong.status_code, 404)
        wrong.close()
        
        # right url
        r = requests.get(__url_settings__)
        self.assertEqual(r.status_code, 200)
        settings = r.json()
        r.close()
        
        # check returned settings
        tt = TimeTable()
        tt.__setstate__(settings)
        self.assertEqual(self.timetable, tt)
    
    
    def test_get_heating(self):
        # wrong url
        wrong = requests.get('http://localhost:4344/wrong')
        self.assertEqual(wrong.status_code, 404)
        wrong.close()
        
        # right url
        r = requests.get(__url_heating__)
        self.assertEqual(r.status_code, 200)
        heating = r.json()
        r.close()
        
        # check returned heating informations
        self.assertEqual(heating['heating_status'], self.heating.status)
        self.assertAlmostEqual(heating['current_temperature'], self.thermometer.temperature, delta=0.1)
        self.assertEqual(heating['target_temperature'], self.timetable.target_temperature())
    
    
    def test_post_wrong_messages(self):
        # wrong url
        wrong = requests.post('http://localhost:4344/wrong', {})
        self.assertEqual(wrong.status_code, 404)
        wrong.close()
        
        # wrong value for status
        wrong = requests.post(__url_settings__, {socket.REQ_SETTINGS_STATUS: 'invalid'})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # wrong value (greater then max allowed)
        wrong = requests.post(__url_settings__, {socket.REQ_SETTINGS_DIFFERENTIAL: 1.1})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # wrong JSON data for settings
        settings = self.timetable.__getstate__()
        settings[timetable.JSON_TEMPERATURES][timetable.JSON_TMAX_STR] = 'inf'
        wrong = requests.post(__url_settings__, {socket.REQ_SETTINGS_ALL: settings})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # invalid JSON syntax for settings
        settings = self.timetable.settings()
        wrong = requests.post(__url_settings__, {socket.REQ_SETTINGS_ALL: settings[0:30]})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # check original paramethers
        self.assertAlmostEqual(self.timetable.differential, 0.5, delta=0.01)
        self.assertAlmostEqual(self.timetable.tmax, 21, delta=0.01)
    
    
    def test_post_right_messages(self):
        # single settings
        p = requests.post(__url_settings__, {socket.REQ_SETTINGS_STATUS: timetable.JSON_STATUS_OFF})
        self.assertEqual(p.status_code, 200)
        self.assertEqual(self.timetable.status, timetable.JSON_STATUS_OFF)
        p.close()
        
        # multiple settings
        q = requests.post(__url_settings__, {socket.REQ_SETTINGS_STATUS: timetable.JSON_STATUS_TMAX,
                                    socket.REQ_SETTINGS_TMAX: 32.3,
                                    socket.REQ_SETTINGS_GRACE_TIME: 'inf'})
        
        self.assertEqual(q.status_code, 200)
        self.assertEqual(self.timetable.status, timetable.JSON_STATUS_TMAX)
        self.assertAlmostEqual(self.timetable.tmax, 32.3, delta=0.01)
        self.assertEqual(self.timetable.grace_time, float('inf'))
        q.close()
        
        # some days
        old_set = self.timetable.__getstate__()
        friday = old_set[timetable.JSON_TIMETABLE][utils.json_get_day_name(5)]
        sunday = old_set[timetable.JSON_TIMETABLE][utils.json_get_day_name(7)]
        
        friday['h12'][0] = 44
        friday['h15'][1] = 45
        sunday['h06'][2] = 46
        sunday['h07'][3] = 47
        
        # all settings
        tt2 = copy.deepcopy(self.timetable)
        tt2.status = timetable.JSON_STATUS_TMAX
        tt2.grace_time = 3600
        tt2.update('thursday', 4, 1, 36.5)
        
        self.assertNotEqual(self.timetable, tt2)  # different before update
        
        s = requests.post(__url_settings__, {socket.REQ_SETTINGS_ALL: tt2.settings()})
        self.assertEqual(s.status_code, 200)
        s.close()
        
        self.assertEqual(self.timetable, tt2)  # equal after update
    
    
    def test_unsupported_http_methods(self):
        pa = requests.patch(__url_settings__, {})
        self.assertEqual(pa.status_code, 501)
        pa.close()
        
        pu = requests.put(__url_settings__, {})
        self.assertEqual(pu.status_code, 501)
        pu.close()
        
        de = requests.delete(__url_heating__)
        self.assertEqual(de.status_code, 501)
        de.close()


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL)
    unittest.main(warnings='ignore')

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
