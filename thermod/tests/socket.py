# -*- coding: utf-8 -*-
"""Test suite for `thermod.socket` module.

Copyright (C) 2017 Simone Rossetto <simros85@gmail.com>

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
import json
import logging
import tempfile
import unittest
import requests

import thermod.socket as socket
from thermod import TimeTable, BaseHeating, ControlThread, utils, const
from thermod.thermometer import FakeThermometer
from thermod.tests.timetable import fill_timetable

__updated__ = '2017-03-01'
__url_settings__ = 'http://localhost:4344/settings'
__url_heating__ = 'http://localhost:4344/heating'


class TestSocket(unittest.TestCase):
    """Test cases for `thermod.socket` module."""

    def setUp(self):
        self.timetable = TimeTable()
        fill_timetable(self.timetable)
        
        self.timetable.filepath = os.path.join(tempfile.gettempdir(), 'timetable.json')
        self.timetable.save()
        
        self.heating = BaseHeating()
        self.thermometer = FakeThermometer()
        
        self.control_socket = ControlThread(self.timetable,
                                            self.heating,
                                            self.thermometer,
                                            const.SOCKET_DEFAULT_HOST,
                                            const.SOCKET_DEFAULT_PORT)
        self.control_socket.start()
   

    def tearDown(self):
        self.control_socket.stop()
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
        self.assertEqual(heating[socket.req_heating_status], self.heating.status)
        self.assertAlmostEqual(heating[socket.req_heating_temperature], self.thermometer.temperature, delta=0.1)
        self.assertEqual(heating[socket.req_heating_target_temp], self.timetable.target_temperature())
    
    
    def test_post_wrong_messages(self):
        # wrong url
        wrong = requests.post('http://localhost:4344/wrong', {})
        self.assertEqual(wrong.status_code, 404)
        wrong.close()
        
        # wrong value for status
        wrong = requests.post(__url_settings__, {socket.req_settings_status: 'invalid'})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # wrong value (greater then max allowed)
        wrong = requests.post(__url_settings__, {socket.req_settings_differential: 1.1})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # wrong JSON data for days
        wrong = requests.post(__url_settings__, {socket.req_settings_days: '{"monday":["invalid"]}'})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # invalid JSON syntax for days
        wrong = requests.post(__url_settings__, {socket.req_settings_days: '{"monday":["missing quote]}'})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # wrong JSON data for settings
        settings = self.timetable.__getstate__()
        settings[const.JSON_TEMPERATURES][const.JSON_TMAX_STR] = 'inf'
        wrong = requests.post(__url_settings__, {socket.req_settings_all: settings})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # invalid JSON syntax for settings
        settings = self.timetable.settings()
        wrong = requests.post(__url_settings__, {socket.req_settings_all: settings[0:30]})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # check original paramethers
        self.assertAlmostEqual(self.timetable.differential, 0.5, delta=0.01)
        self.assertAlmostEqual(self.timetable.tmax, 21, delta=0.01)
    
    
    def test_post_right_messages(self):
        # single settings
        p = requests.post(__url_settings__, {socket.req_settings_status: const.JSON_STATUS_OFF})
        self.assertEqual(p.status_code, 200)
        self.assertEqual(self.timetable.status, const.JSON_STATUS_OFF)
        p.close()
        
        # multiple settings
        q = requests.post(__url_settings__, {socket.req_settings_status: const.JSON_STATUS_TMAX,
                                    socket.req_settings_tmax: 32.3,
                                    socket.req_settings_grace_time: 'inf'})
        
        self.assertEqual(q.status_code, 200)
        self.assertEqual(self.timetable.status, const.JSON_STATUS_TMAX)
        self.assertAlmostEqual(self.timetable.tmax, 32.3, delta=0.01)
        self.assertEqual(self.timetable.grace_time, float('inf'))
        q.close()
        
        # some days
        old_set = self.timetable.__getstate__()
        friday = old_set[const.JSON_TIMETABLE][utils.json_get_day_name(5)]
        sunday = old_set[const.JSON_TIMETABLE][utils.json_get_day_name(7)]
        
        friday['h12'][0] = 44
        friday['h15'][1] = 45
        sunday['h06'][2] = 46
        sunday['h07'][3] = 47
        
        r = requests.post(__url_settings__,
            {socket.req_settings_days:
                json.dumps({utils.json_get_day_name(5): friday,
                            utils.json_get_day_name(7): sunday})})
        
        self.assertEqual(r.status_code, 200)
        new_set = self.timetable.__getstate__()
        new_friday = new_set[const.JSON_TIMETABLE][utils.json_get_day_name(5)]
        new_sunday = new_set[const.JSON_TIMETABLE][utils.json_get_day_name(7)]
        
        self.assertEqual(new_friday['h12'][0], 44)
        self.assertEqual(new_friday['h15'][1], 45)
        self.assertEqual(new_sunday['h06'][2], 46)
        self.assertEqual(new_sunday['h07'][3], 47)
        
        # all settings
        tt2 = copy.deepcopy(self.timetable)
        tt2.status = const.JSON_STATUS_TMAX
        tt2.grace_time = 3600
        tt2.update('thursday', 4, 1, 36.5)
        
        self.assertNotEqual(self.timetable, tt2)  # different before update
        
        s = requests.post(__url_settings__, {socket.req_settings_all: tt2.settings()})
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
