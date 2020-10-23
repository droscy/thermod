# -*- coding: utf-8 -*-
"""Test suite for `TimeTable` class.

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
import time
import locale
import unittest
import tempfile
import threading
from jsonschema import ValidationError
from datetime import datetime, timedelta
from thermod import timetable, ThermodStatus
from thermod.common import HVAC_HEATING, HVAC_COOLING
from thermod.timetable import TimeTable, ShouldBeOn, JsonValueError
from thermod.heating import BaseHeating

__updated__ = '2020-10-22'


# state saved with Thermod version 1.2
_json_state_v1 = '''
{
  "status": "auto",
  "differential": 0.5,
  "grace_time": null,
  "temperatures": {
    "t0": 10.0,
    "tmin": 17.0,
    "tmax": 20.0
  },
  "timetable": {
    "monday": {
      "h00": ["tmin","tmin","tmin","tmin"],
      "h01": ["tmin","tmin","tmin","tmin"],
      "h02": ["tmin","tmin","tmin","tmin"],
      "h03": ["tmin","tmin","tmin","tmin"],
      "h04": ["tmin","tmin","tmin","tmin"],
      "h05": ["tmin","tmin","tmin","tmin"],
      "h06": ["tmin","tmax","tmax","tmax"],
      "h07": ["tmax","tmax","tmax","tmax"],
      "h08": ["tmax","tmax","tmin","tmin"],
      "h09": ["tmin","tmin","tmin","tmin"],
      "h10": ["tmin","tmin","tmin","tmin"],
      "h11": ["tmin","tmin","tmin","tmin"],
      "h12": ["tmin","tmin","tmin","tmin"],
      "h13": ["tmin","tmin","tmin","tmin"],
      "h14": ["tmin","tmin","tmin","tmin"],
      "h15": ["tmin","tmin","tmax","tmax"],
      "h16": ["tmax","tmax","tmax","tmax"],
      "h17": ["tmax","tmax","tmax","tmax"],
      "h18": ["tmax","tmax","tmax","tmax"],
      "h19": ["tmax","tmax","tmax","tmax"],
      "h20": ["tmax","tmax","tmax","tmax"],
      "h21": ["tmax","tmax","tmax","tmax"],
      "h22": ["tmax","tmax","tmax","tmax"],
      "h23": ["tmax","tmin","tmin","tmin"]
    },
    "tuesday": {
      "h00": ["tmin","tmin","tmin","tmin"],
      "h01": ["tmin","tmin","tmin","tmin"],
      "h02": ["tmin","tmin","tmin","tmin"],
      "h03": ["tmin","tmin","tmin","tmin"],
      "h04": ["tmin","tmin","tmin","tmin"],
      "h05": ["tmin","tmin","tmin","tmin"],
      "h06": ["tmin","tmax","tmax","tmax"],
      "h07": ["tmax","tmax","tmax","tmax"],
      "h08": ["tmax","tmax","tmin","tmin"],
      "h09": ["tmin","tmin","tmin","tmin"],
      "h10": ["tmin","tmin","tmin","tmin"],
      "h11": ["tmin","tmin","tmin","tmin"],
      "h12": ["tmin","tmin","tmin","tmin"],
      "h13": ["tmin","tmin","tmin","tmin"],
      "h14": ["tmin","tmin","tmin","tmin"],
      "h15": ["tmin","tmin","tmax","tmax"],
      "h16": ["tmax","tmax","tmax","tmax"],
      "h17": ["tmax","tmax","tmax","tmax"],
      "h18": ["tmax","tmax","tmax","tmax"],
      "h19": ["tmax","tmax","tmax","tmax"],
      "h20": ["tmax","tmax","tmax","tmax"],
      "h21": ["tmax","tmax","tmax","tmax"],
      "h22": ["tmax","tmax","tmax","tmax"],
      "h23": ["tmax","tmin","tmin","tmin"]
    },
    "wednesday": {

      "h00": ["tmin","tmin","tmin","tmin"],
      "h01": ["tmin","tmin","tmin","tmin"],
      "h02": ["tmin","tmin","tmin","tmin"],
      "h03": ["tmin","tmin","tmin","tmin"],
      "h04": ["tmin","tmin","tmin","tmin"],
      "h05": ["tmin","tmin","tmin","tmin"],
      "h06": ["tmin","tmax","tmax","tmax"],
      "h07": ["tmax","tmax","tmax","tmax"],
      "h08": ["tmax","tmax","tmin","tmin"],
      "h09": ["tmin","tmin","tmin","tmin"],
      "h10": ["tmin","tmin","tmin","tmin"],
      "h11": ["tmin","tmin","tmin","tmin"],
      "h12": ["tmin","tmin","tmin","tmin"],
      "h13": ["tmin","tmin","tmin","tmin"],
      "h14": ["tmin","tmin","tmin","tmin"],
      "h15": ["tmin","tmin","tmax","tmax"],
      "h16": ["tmax","tmax","tmax","tmax"],
      "h17": ["tmax","tmax","tmax","tmax"],
      "h18": ["tmax","tmax","tmax","tmax"],
      "h19": ["tmax","tmax","tmax","tmax"],
      "h20": ["tmax","tmax","tmax","tmax"],
      "h21": ["tmax","tmax","tmax","tmax"],
      "h22": ["tmax","tmax","tmax","tmax"],
      "h23": ["tmax","tmin","tmin","tmin"]
    },
    "thursday": {
      "h00": ["tmin","tmin","tmin","tmin"],
      "h01": ["tmin","tmin","tmin","tmin"],
      "h02": ["tmin","tmin","tmin","tmin"],
      "h03": ["tmin","tmin","tmin","tmin"],
      "h04": ["tmin","tmin","tmin","tmin"],
      "h05": ["tmin","tmin","tmin","tmin"],
      "h06": ["tmin","tmax","tmax","tmax"],
      "h07": ["tmax","tmax","tmax","tmax"],
      "h08": ["tmax","tmax","tmin","tmin"],
      "h09": ["tmin","tmin","tmin","tmin"],
      "h10": ["tmin","tmin","tmin","tmin"],
      "h11": ["tmin","tmin","tmin","tmin"],
      "h12": ["tmin","tmin","tmin","tmin"],
      "h13": ["tmin","tmin","tmin","tmin"],
      "h14": ["tmin","tmin","tmin","tmin"],
      "h15": ["tmin","tmin","tmax","tmax"],
      "h16": ["tmax","tmax","tmax","tmax"],
      "h17": ["tmax","tmax","tmax","tmax"],
      "h18": ["tmax","tmax","tmax","tmax"],
      "h19": ["tmax","tmax","tmax","tmax"],
      "h20": ["tmax","tmax","tmax","tmax"],
      "h21": ["tmax","tmax","tmax","tmax"],
      "h22": ["tmax","tmax","tmax","tmax"],
      "h23": ["tmax","tmin","tmin","tmin"]
    },
    "friday": {
      "h00": ["tmin","tmin","tmin","tmin"],
      "h01": ["tmin","tmin","tmin","tmin"],
      "h02": ["tmin","tmin","tmin","tmin"],
      "h03": ["tmin","tmin","tmin","tmin"],
      "h04": ["tmin","tmin","tmin","tmin"],
      "h05": ["tmin","tmin","tmin","tmin"],
      "h06": ["tmin","tmax","tmax","tmax"],
      "h07": ["tmax","tmax","tmax","tmax"],
      "h08": ["tmax","tmax","tmin","tmin"],
      "h09": ["tmin","tmin","tmin","tmin"],
      "h10": ["tmin","tmin","tmin","tmin"],
      "h11": ["tmin","tmin","tmin","tmin"],
      "h12": ["tmin","tmin","tmin","tmin"],
      "h13": ["tmin","tmin","tmin","tmin"],
      "h14": ["tmin","tmin","tmin","tmin"],
      "h15": ["tmin","tmin","tmax","tmax"],
      "h16": ["tmax","tmax","tmax","tmax"],
      "h17": ["tmax","tmax","tmax","tmax"],
      "h18": ["tmax","tmax","tmax","tmax"],
      "h19": ["tmax","tmax","tmax","tmax"],
      "h20": ["tmax","tmax","tmax","tmax"],
      "h21": ["tmax","tmax","tmax","tmax"],
      "h22": ["tmax","tmax","tmax","tmax"],
      "h23": ["tmax","tmin","tmin","tmin"]
    },
    "saturday": {
      "h00": ["tmin","tmin","tmin","tmin"],
      "h01": ["tmin","tmin","tmin","tmin"],
      "h02": ["tmin","tmin","tmin","tmin"],
      "h03": ["tmin","tmin","tmin","tmin"],
      "h04": ["tmin","tmin","tmin","tmin"],
      "h05": ["tmin","tmin","tmin","tmin"],
      "h06": ["tmin","tmin","tmin","tmin"],
      "h07": ["tmin","tmin","tmin","tmin"],
      "h08": ["tmax","tmax","tmax","tmax"],
      "h09": ["tmax","tmax","tmax","tmax"],
      "h10": ["tmax","tmax","tmax","tmax"],
      "h11": ["tmax","tmax","tmax","tmax"],
      "h12": ["tmax","tmax","tmax","tmax"],
      "h13": ["tmax","tmax","tmax","tmax"],
      "h14": ["tmax","tmax","tmax","tmax"],
      "h15": ["tmax","tmax","tmax","tmax"],
      "h16": ["tmax","tmax","tmax","tmax"],
      "h17": ["tmax","tmax","tmax","tmax"],
      "h18": ["tmax","tmax","tmax","tmax"],
      "h19": ["tmax","tmax","tmax","tmax"],
      "h20": ["tmax","tmax","tmax","tmax"],
      "h21": ["tmax","tmax","tmax","tmax"],
      "h22": ["tmin","tmin","tmin","tmin"],
      "h23": ["tmin","tmin","tmin","tmin"]
    },
    "sunday": {
      "h00": ["tmin","tmin","tmin","tmin"],
      "h01": ["tmin","tmin","tmin","tmin"],
      "h02": ["tmin","tmin","tmin","tmin"],
      "h03": ["tmin","tmin","tmin","tmin"],
      "h04": ["tmin","tmin","tmin","tmin"],
      "h05": ["tmin","tmin","tmin","tmin"],
      "h06": ["tmin","tmin","tmin","tmin"],
      "h07": ["tmin","tmin","tmin","tmin"],
      "h08": ["tmax","tmax","tmax","tmax"],
      "h09": ["tmax","tmax","tmax","tmax"],
      "h10": ["tmax","tmax","tmax","tmax"],
      "h11": ["tmax","tmax","tmax","tmax"],
      "h12": ["tmax","tmax","tmax","tmax"],
      "h13": ["tmax","tmax","tmax","tmax"],
      "h14": ["tmax","tmax","tmax","tmax"],
      "h15": ["tmax","tmax","tmax","tmax"],
      "h16": ["tmax","tmax","tmax","tmax"],
      "h17": ["tmax","tmax","tmax","tmax"],
      "h18": ["tmax","tmax","tmax","tmax"],
      "h19": ["tmax","tmax","tmax","tmax"],
      "h20": ["tmax","tmax","tmax","tmax"],
      "h21": ["tmax","tmax","tmax","tmax"],
      "h22": ["tmax","tmax","tmax","tmax"],
      "h23": ["tmax","tmax","tmax","tmax"]
    }
  }
}'''


def fill_timetable(tt):
    """Fill a `TimeTable` object with test values."""
    
    tt.t0 = 5
    tt.tmin = 17
    tt.tmax = 21
    
    tt.differential = 0.5
    tt.grace_time = 180
    
    t0 = timetable.JSON_T0_STR
    tmin = timetable.JSON_TMIN_STR
    tmax = timetable.JSON_TMAX_STR
    
    for day in range(7):
        for hour in range(7):
            for quarter in range(4):
                tt.update(day, hour, quarter, tmin)
        
        for hour in range(7,9):
            for quarter in range(4):
                tt.update(day, hour, quarter, tmax)
        
        for hour in range(9,16):
            for quarter in range(4):
                tt.update(day, hour, quarter, tmin)
        
        for hour in range(16,23):
            for quarter in range(4):
                tt.update(day, hour, quarter, tmax)
        
        hour = 23
        for quarter in range(4):
            tt.update(day, hour, quarter, t0)
    
    tt.mode = timetable.JSON_MODE_AUTO


class TestTimeTable(unittest.TestCase):
    """Test cases for `TimeTable` class."""

    def setUp(self):
        self.timetable = TimeTable()
        self.heating = BaseHeating()
    
    def tearDown(self):
        pass
    
    def test_filepath(self):
        # empty tiletable
        self.assertRaises(RuntimeError, self.timetable.reload)
        self.assertRaises(RuntimeError, self.timetable.save)
        
        # non existing file
        with self.assertRaises(FileNotFoundError):
            self.timetable.filepath = '/tmp/non_existing_file'
            self.timetable.reload()
        
        # invalid json file
        invalid_json_file = os.path.join(tempfile.gettempdir(), 'thermod-invalid-json.conf')
        
        with open(invalid_json_file, 'w') as file:
            file.write('[global] invalid = not json')
        
        with self.assertRaises(ValueError):
            self.timetable.filepath = invalid_json_file
            self.timetable.reload()
        
        try:
            os.remove(invalid_json_file)
        except FileNotFoundError:
            pass
    
    
    def test_mode(self):
        for mode in timetable.JSON_ALL_MODES:
            self.timetable.mode = mode
            self.assertEqual(mode, self.timetable.mode)
        
        mode = 'invalid'
        self.assertNotIn(mode, timetable.JSON_ALL_MODES)
        with self.assertRaises(JsonValueError):
            self.timetable.mode = mode
    
    
    def test_differential(self):
        # valid float values (rounded up to 1st decimal number)
        for d in range(0,101):
            diff = d/100
            self.timetable.differential = diff
            self.assertAlmostEqual(round(diff,1),
                                   self.timetable.differential,
                                   places=1)
        
        # valid string values (rounded up to 1st decimal number)
        for d in range(0,101):
            diff = d/100
            self.timetable.differential = format(diff, '+.2f')
            self.assertAlmostEqual(round(diff,1),
                                   self.timetable.differential,
                                   places=1)
        
        # invalid values
        with self.assertRaises(JsonValueError):
            self.timetable.differential = 1.1
        
        with self.assertRaises(JsonValueError):
            self.timetable.differential = -0.15
        
        with self.assertRaises(JsonValueError):
            self.timetable.differential = 'invalid'
    
    
    def test_grace_time(self):
        # valid values
        for grace in range(0, 12000, 120):
            self.timetable.grace_time = grace
            self.assertEqual(grace, self.timetable.grace_time)
        
        # test float inf value
        self.timetable.grace_time = 'inf'
        self.assertEqual(float('inf'), self.timetable.grace_time)
        
        self.timetable.grace_time = float('inf')
        self.assertEqual(float('inf'), self.timetable.grace_time)
        
        # invalid values
        with self.assertRaises(JsonValueError):
            self.timetable.grace_time = -300
        
        with self.assertRaises(JsonValueError):
            self.timetable.grace_time = 'invalid'
    
    
    def test_t0(self):
        # valid float values (rounded up to 1st decimal number)
        for t in range(100,150):
            temp = t/10
            self.timetable.t0 = temp
            self.assertAlmostEqual(temp, self.timetable.t0, places=1)
        
        # valid string values (rounded up to 1st decimal number)
        for t in range(100,150):
            temp = t/10
            self.timetable.t0 = format(temp, '+.1f')
            self.assertAlmostEqual(temp, self.timetable.t0, places=1)
        
        # invalid values
        for t in timetable.JSON_ALL_TEMPERATURES:
            with self.assertRaises(JsonValueError):
                self.timetable.t0 = t
        
        with self.assertRaises(JsonValueError):
            self.timetable.t0 = 'invalid'
        
        with self.assertRaises(JsonValueError):
            self.timetable.tmax = 'nan'
    
    
    def test_tmin(self):
        # valid float values (rounded up to 1st decimal number)
        for t in range(130,180):
            temp = t/10
            self.timetable.tmin = temp
            self.assertAlmostEqual(temp, self.timetable.tmin, places=1)
        
        # valid string values (rounded up to 1st decimal number)
        for t in range(130,180):
            temp = t/10
            self.timetable.tmin = format(temp, '+.1f')
            self.assertAlmostEqual(temp, self.timetable.tmin, places=1)
        
        # invalid values
        for t in timetable.JSON_ALL_TEMPERATURES:
            with self.assertRaises(JsonValueError):
                self.timetable.tmin = t
        
        with self.assertRaises(JsonValueError):
            self.timetable.tmin = 'invalid'
        
        with self.assertRaises(JsonValueError):
            self.timetable.tmax = '-inf'
    
    
    def test_tmax(self):
        # valid float values (rounded up to 1st decimal number)
        for t in range(170,210):
            temp = t/10
            self.timetable.tmax = temp
            self.assertAlmostEqual(temp, self.timetable.tmax, places=1)
        
        # valid string values (rounded up to 1st decimal number)
        for t in range(170,210):
            temp = t/10
            self.timetable.tmax = format(temp, '+.1f')
            self.assertAlmostEqual(temp, self.timetable.tmax, places=1)
        
        # invalid values
        for t in timetable.JSON_ALL_TEMPERATURES:
            with self.assertRaises(JsonValueError):
                self.timetable.tmax = t
        
        with self.assertRaises(JsonValueError):
            self.timetable.tmax = 'invalid'
        
        with self.assertRaises(JsonValueError):
            self.timetable.tmax = 'inf'
    
    
    def test_hvac_mode(self):
        self.assertEqual(self.timetable.hvac_mode, HVAC_HEATING)
        
        self.timetable.hvac_mode = HVAC_COOLING
        self.assertEqual(self.timetable.hvac_mode, HVAC_COOLING)
        
        with self.assertRaises(JsonValueError):
            self.timetable.hvac_mode = 'othervalue'
    
    
    def test_degrees(self):
        # no main temperatures already set, thus exception
        self.assertRaises(RuntimeError,self.timetable.degrees, 't0')
        
        # set main temperatures
        self.timetable.t0 = 5
        self.timetable.tmin = 17
        self.timetable.tmax = 21
        
        self.assertEqual(self.timetable.degrees(timetable.JSON_T0_STR), 5)
        self.assertEqual(self.timetable.degrees(timetable.JSON_TMIN_STR), 17)
        self.assertEqual(self.timetable.degrees(timetable.JSON_TMAX_STR), 21)
        
        for temp in range(50):
            self.assertEqual(self.timetable.degrees(temp), temp)
            self.assertEqual(self.timetable.degrees(format(temp,'-.1f')), temp)
            
            self.timetable.tmax = temp
            self.assertEqual(self.timetable.degrees('tmax'), temp)
    
    
    def test_save_and_load(self):
        # temporary file to save data
        (file1,filepath1) = tempfile.mkstemp(suffix='.tmp', prefix='thermod')
        (file2,filepath2) = tempfile.mkstemp(suffix='.tmp', prefix='thermod')
        
        # timetable has no filepath cannot be saved
        self.assertRaises(RuntimeError,self.timetable.save)
        
        # setting filepath
        self.timetable.filepath = filepath1
        
        # timetable is empty cannot be saved
        self.assertRaises(ValidationError,self.timetable.save)
        
        # filling the timetable
        fill_timetable(self.timetable)
        
        # saving and loading two times
        self.timetable.save()
        tt1 = TimeTable(filepath1)
        self.assertEqual(self.timetable, tt1)
        self.assertEqual(self.timetable.mode, tt1.mode)
        
        tt1.save(filepath2)
        tt2 = TimeTable()
        tt2.filepath = filepath2
        tt2.reload()
        self.assertEqual(self.timetable, tt2)
        self.assertEqual(self.timetable.mode, tt2.mode)
        
        # removing temporary files
        os.close(file1)
        os.remove(filepath1)
        os.close(file2)
        os.remove(filepath2)
    
    
    def test_equality_and_copy_operators(self):
        tt = TimeTable()
        
        fill_timetable(self.timetable)
        fill_timetable(tt)
        
        self.assertEqual(self.timetable, tt)
        self.assertEqual(self.timetable.mode, tt.mode)
        
        # test copy operators
        tt2 = copy.deepcopy(self.timetable)
        self.assertEqual(self.timetable, tt2)
        self.assertEqual(self.timetable.mode, tt2.mode)
        
        # changing the mode makes two timetable different
        tt2.mode = timetable.JSON_MODE_OFF
        self.assertNotEqual(self.timetable, tt2)
        self.assertNotEqual(self.timetable.mode, tt2.mode)
        
        # change other settings and test inequality
        tt.grace_time = 1200
        self.assertNotEqual(self.timetable, tt)
        self.assertNotEqual(self.timetable.grace_time, tt.grace_time)
        
        tt2.update(3,15,0,34)
        self.assertNotEqual(self.timetable, tt2)
    
    
    def test_equality_regardless_of_inertia(self):
        tt = TimeTable(inertia=1)
        
        fill_timetable(self.timetable)
        fill_timetable(tt)
        
        self.assertEqual(self.timetable, tt)
        
        # now change inertia
        tt._inertia = 2
        self.assertEqual(self.timetable, tt)
    
        # now change again
        tt._inertia = 3
        self.assertEqual(self.timetable, tt)
    
    
    def test_update(self):
        # TODO this test is not reliable, need improvments or revisitation
        self.assertRaises(JsonValueError, self.timetable.update, 'invalid', 10, 0, timetable.JSON_TMAX_STR)
        self.assertRaises(JsonValueError, self.timetable.update, 8, 10, 0, timetable.JSON_T0_STR)
        self.assertRaises(JsonValueError, self.timetable.update, 4, 'invalid', 0, timetable.JSON_TMIN_STR)
        self.assertRaises(JsonValueError, self.timetable.update, 4, 23, 5, timetable.JSON_TMAX_STR)
        self.assertRaises(JsonValueError, self.timetable.update, 4, 26, 2, timetable.JSON_TMIN_STR)
        self.assertRaises(JsonValueError, self.timetable.update, 7, 11, 1, 'invalid')
        self.assertRaises(JsonValueError, self.timetable.update, 4, 11, 'invalid', timetable.JSON_TMAX_STR)
    
    
    def test_locale(self):
        # setlocale doesn't work on Windows
        if os.name == 'posix':
            locale.setlocale(locale.LC_ALL,'it_IT.utf8')
            
            fill_timetable(self.timetable)
            
            self.assertIsNone(self.timetable.update('Lun',10,1,30))
            self.assertIsNone(self.timetable.update('mer',11,2,20))
            settings = self.timetable.__getstate__()
            
            day = timetable.json_get_day_name(1)
            hour = timetable.json_format_hour(10)
            quarter = 1
            t1 = timetable.temperature_to_float(settings[timetable.JSON_TIMETABLE][day][hour][quarter])
            t2 = timetable.temperature_to_float(30)
            self.assertEqual(t1, t2)
    
            day = timetable.json_get_day_name(3)
            hour = timetable.json_format_hour(11)
            quarter = 2
            t1 = timetable.temperature_to_float(settings[timetable.JSON_TIMETABLE][day][hour][quarter])
            t2 = timetable.temperature_to_float(20)
            self.assertEqual(t1, t2)
    
    
    def test_timetable_01(self):  # test t0 mode
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = timetable.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.mode = timetable.JSON_MODE_T0
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        
        for temp in range(-10,5):
            self.assertTrue(self.timetable.should_the_heating_be_on(temp, self.heating.status))
        
        # Not testing temp equal to t0 (5 degrees) because the result
        # depends by both grace time and differential. More on other tests.
        
        for temp in range(6,15):
            self.assertFalse(self.timetable.should_the_heating_be_on(temp, self.heating.status))
    
    
    def test_timetable_02(self):  # test tmin mode
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = timetable.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.mode = timetable.JSON_MODE_TMIN
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        
        for temp in range(0,17):
            self.assertTrue(self.timetable.should_the_heating_be_on(temp, self.heating.status))
        
        # Not testing temp equal to tmin (17 degrees) because the result
        # depends by both grace time and differential. More on other tests.
        
        for temp in range(18,21):
            self.assertFalse(self.timetable.should_the_heating_be_on(temp, self.heating.status))
        
    
    def test_timetable_03(self):  # test tmax mode
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = timetable.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.mode = timetable.JSON_MODE_TMAX
        self.timetable.update(day,hour,quarter,timetable.JSON_T0_STR)
        
        for temp in range(10,21):
            self.assertTrue(self.timetable.should_the_heating_be_on(temp, self.heating.status))
        
        # Not testing temp equal to tmax (21 degrees) because the result
        # depends by both grace time and differential. More on other tests.
        
        for temp in range(22,27):
            self.assertFalse(self.timetable.should_the_heating_be_on(temp, self.heating.status))
    
    
    def test_timetable_04(self):  # test on/off modes
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = timetable.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.mode = timetable.JSON_MODE_ON
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        self.assertTrue(self.timetable.should_the_heating_be_on(3, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(10, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(20, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(22, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(25, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(30, self.heating.status))
        
        self.timetable.mode = timetable.JSON_MODE_OFF
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        self.assertFalse(self.timetable.should_the_heating_be_on(3, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(10, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(20, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(22, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(25, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(30, self.heating.status))
    
    
    def test_timetable_05(self):  # test auto mode
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = timetable.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.mode = timetable.JSON_MODE_AUTO
        
        # current target t0
        self.timetable.update(day,hour,quarter,timetable.JSON_T0_STR)
        self.assertTrue(self.timetable.should_the_heating_be_on(3, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(10, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(20, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(22, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(25, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(30, self.heating.status))
        
        # current target tmin
        self.timetable.update(day,hour,quarter,timetable.JSON_TMIN_STR)
        self.assertTrue(self.timetable.should_the_heating_be_on(3, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(10, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(20, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(22, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(25, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(30, self.heating.status))
        
        # current target tmax
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        self.assertTrue(self.timetable.should_the_heating_be_on(3, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(10, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(20, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(22, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(25, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(30, self.heating.status))
        
        # current target manual temperature
        self.timetable.update(day,hour,quarter,27.5)
        self.assertTrue(self.timetable.should_the_heating_be_on(3, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(10, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(20, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(22, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(25, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(30, self.heating.status))
    
    
    def test_timetable_06(self):
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = timetable.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.mode = timetable.JSON_MODE_AUTO
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        
        # check if the heating should be on
        self.assertTrue(self.timetable.should_the_heating_be_on(19, self.heating.status))
        
        # virtually switching on and set internal state
        self.heating.switch_on()
        
        # the temperature start increasing
        self.assertTrue(self.timetable.should_the_heating_be_on(20, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(20.5, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(21, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(21.4, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(21.5, self.heating.status))
        
        # virtually switching off and set internal state
        self.heating.switch_off()
        
        # the temperature start decreasing
        self.assertFalse(self.timetable.should_the_heating_be_on(21.4, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(21, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(20.6, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(20.5, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(20, self.heating.status))
    
    
    def test_timetable_06b(self):  # the same of test 06 with inertia==2
        fill_timetable(self.timetable)
        self.timetable._inertia = 2
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = timetable.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.mode = timetable.JSON_MODE_AUTO
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        
        # check if the heating should be on
        self.assertTrue(self.timetable.should_the_heating_be_on(19, self.heating.status))
        
        # virtually switching on and set internal state
        self.heating.switch_on()
        
        # the temperature start increasing
        self.assertTrue(self.timetable.should_the_heating_be_on(19.5, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(20.0, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(20.5, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(20.9, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(21.0, self.heating.status))  # off at target
        self.assertFalse(self.timetable.should_the_heating_be_on(21.5, self.heating.status))
        
        # virtually switching off and set internal state
        self.heating.switch_off()
        
        # the temperature start decreasing
        self.assertFalse(self.timetable.should_the_heating_be_on(21.0, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(20.5, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(20.1, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(20.0, self.heating.status))  # on at target-2*diff
        self.assertTrue(self.timetable.should_the_heating_be_on(19.5, self.heating.status))
    
    
    def test_timetable_06c(self):  # the same of test 06 with inertia==3
        fill_timetable(self.timetable)
        self.timetable._inertia = 3
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = timetable.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.mode = timetable.JSON_MODE_AUTO
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        
        # check if the heating should be on
        self.assertTrue(self.timetable.should_the_heating_be_on(19, self.heating.status))
        
        # virtually switching on and set internal state
        self.heating.switch_on()
        
        # the temperature start increasing
        self.assertTrue(self.timetable.should_the_heating_be_on(19.5, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(20.0, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(20.4, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(20.5, self.heating.status))  # off at target-diff
        self.assertFalse(self.timetable.should_the_heating_be_on(21.0, self.heating.status))
        
        # virtually switching off and set internal state
        self.heating.switch_off()
        
        # the temperature start decreasing
        self.assertFalse(self.timetable.should_the_heating_be_on(21.0, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(20.5, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(20.1, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(20.0, self.heating.status))  # on at target-2*diff
        self.assertTrue(self.timetable.should_the_heating_be_on(19.5, self.heating.status))
    
    
    def test_timetable_06_cooling(self):  # # the same of test 06 with hvac_mode==cooling
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = timetable.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.mode = timetable.JSON_MODE_AUTO
        self.timetable.hvac_mode = HVAC_COOLING
        self.timetable.tmax = 30
        self.timetable.tmin = 24
        self.timetable.update(day,hour,quarter,timetable.JSON_TMIN_STR)  # tmin mean 'off' even for cooling
        
        # the cooling should be on if current temp above tmax
        self.assertTrue(self.timetable.should_the_heating_be_on(31, self.heating.status))
        
        # the cooling should be off for tmin in auto mode
        self.assertFalse(self.timetable.should_the_heating_be_on(25, self.heating.status))
        
        # the cooling should be on now
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)  # tmax mean 'on' even for cooling
        self.assertTrue(self.timetable.should_the_heating_be_on(25, self.heating.status))
        
        # virtually switching on and set internal state
        self.heating.switch_on()
        
        # the temperature start decreasing
        self.assertTrue(self.timetable.should_the_heating_be_on(24.8, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(24.5, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(24.2, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(23.9, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(23.4, self.heating.status))
        
        # virtually switching off and set internal state
        self.heating.switch_off()
        
        # the temperature start increasing
        self.assertFalse(self.timetable.should_the_heating_be_on(23.7, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(24.0, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(24.4, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(24.9, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(25.1, self.heating.status))
    
    
    def test_timetable_07(self):
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = timetable.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.mode = timetable.JSON_MODE_AUTO
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        
        # the current temperature fell below target 2 hours ago, more than grace time
        self.heating._is_on = False
        self.timetable._last_below_tgt_temp_timestamp = (now - timedelta(seconds=7200)).timestamp()
        self.assertTrue(self.timetable.should_the_heating_be_on(20.9, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(21, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(21.1, self.heating.status))
    
    
    def test_timetable_08(self):
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = timetable.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.mode = timetable.JSON_MODE_AUTO
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        self.timetable.grace_time = 3600
        
        # the current temperature fell below target 30 minutes ago, less than grace time
        self.heating._is_on = False
        self.timetable._last_below_tgt_temp_timestamp = (now - timedelta(seconds=1800)).timestamp()
        self.assertTrue(self.timetable.should_the_heating_be_on(20.5, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(20.6, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(21, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(21.5, self.heating.status))
    
    
    def test_timetable_09(self):
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = timetable.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.mode = timetable.JSON_MODE_AUTO
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        self.timetable.grace_time = 60
        self.heating.switch_on()
        
        # the heating is on and it remains on untill target temperature
        # plus differential
        self.assertTrue(self.timetable.should_the_heating_be_on(21.1, self.heating.status))
        
        # I simulate the time passing by changing the target temperature
        # next quarter is tmin
        self.timetable.update(day,hour,quarter,timetable.JSON_TMIN_STR)
        self.assertFalse(self.timetable.should_the_heating_be_on(21, self.heating.status))
        self.heating.switch_off()
        
        # even if next quarter is tmax again, the grace time is not passed and
        # the heating remains off
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        self.assertFalse(self.timetable.should_the_heating_be_on(21, self.heating.status))
    
    
    def test_timetable_10(self):
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = timetable.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.mode = timetable.JSON_MODE_AUTO
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        self.timetable.grace_time = 2
        self.heating.switch_on()
        
        # the heating is on
        self.assertTrue(self.timetable.should_the_heating_be_on(21.1, self.heating.status))
        
        # sleeps 3 seconds to exceed the grace time, the heating is then off
        time.sleep(3)
        self.assertFalse(self.timetable.should_the_heating_be_on(21.1, self.heating.status))
    
    
    def test_target_temperature(self):
        fill_timetable(self.timetable)
        
        time = datetime(2016,2,14,17,23,0)
        day = time.strftime('%w')
        hour = timetable.json_format_hour(time.hour)
        quarter = int(time.minute // 15)
        
        self.assertAlmostEqual(self.timetable.target_temperature(time), self.timetable.tmax, delta=0.01)
        t = 45.0
        self.timetable.update(day, hour, quarter, t)
        self.assertAlmostEqual(self.timetable.target_temperature(time), t, delta=0.01)
        
        self.assertAlmostEqual(self.timetable.target_temperature(datetime(2016,2,10,9,34,0)), self.timetable.tmin, delta=0.01)
        self.assertAlmostEqual(self.timetable.target_temperature(datetime(2016,2,10,23,34,0)), self.timetable.t0, delta=0.01)
        
        self.timetable.mode = timetable.JSON_MODE_ON
        self.assertEqual(self.timetable.target_temperature(time), None)
        
        self.timetable.mode = timetable.JSON_MODE_OFF
        self.assertEqual(self.timetable.target_temperature(time), None)
        
        self.timetable.mode = timetable.JSON_MODE_TMAX
        self.assertAlmostEqual(self.timetable.target_temperature(time), self.timetable.tmax, delta=0.01)
        
        self.timetable.mode = timetable.JSON_MODE_TMIN
        self.assertAlmostEqual(self.timetable.target_temperature(time), self.timetable.tmin, delta=0.01)
        
        self.timetable.mode = timetable.JSON_MODE_T0
        self.assertAlmostEqual(self.timetable.target_temperature(time), self.timetable.t0, delta=0.01)
    
    def test_load_old_state(self):
        """Try to load on old JSON schema."""
        
        # good old schema
        self.timetable.load(_json_state_v1)
        
        # mixed schema (old with some changes)
        with self.assertRaises(ValidationError):
            self.timetable.load(_json_state_v1.replace('status', 'mode'))
    
    def test_old_state_adapter(self):
        """Check if the adapter is transparent in case of valid new state."""
        self.timetable.load(_json_state_v1)
        state = self.timetable.__getstate__()
        self.assertEqual(state, self.timetable._old_state_adapter(state))
    
    # TODO write more concurrent tests
    def test_threading_01(self):
        fill_timetable(self.timetable)
        
        self.timetable.tmax = 30
        self.timetable.mode = timetable.JSON_MODE_TMAX
        
        # initial status, the heating should be on
        self.assertTrue(self.timetable.should_the_heating_be_on(20, self.heating.status))
        
        # creating main lock
        lock = threading.Condition()
        
        # creating updating thread
        thread = threading.Thread(target=self.thread_change_mode, args=(lock,))
        
        # the lock is acquired, then the thread that changes a parameter is
        # executed and the assert is checked again, if the lock works the
        # assert is still True
        with lock:
            thread.start()
            self.assertTrue(self.timetable.should_the_heating_be_on(20, self.heating.status))
        
        # the assert become False after the execution of the thread
        thread.join()
        self.assertFalse(self.timetable.should_the_heating_be_on(20, self.heating.status))
    
    def thread_change_mode(self, lock):
        self.assertTrue(self.timetable.should_the_heating_be_on(20, self.heating.status))
        
        with lock:
            self.timetable.mode = timetable.JSON_MODE_OFF
            self.assertFalse(self.timetable.should_the_heating_be_on(20, self.heating.status))

    def test_should_be_on(self):
        s1 = ShouldBeOn(True)
        self.assertTrue(s1)
        
        st2 = ThermodStatus(time.time(), timetable.JSON_MODE_AUTO, 1, 5, 10)
        s2 = ShouldBeOn(False, st2)
        self.assertFalse(s2)
        
        st3 = ThermodStatus(time.time(), timetable.JSON_MODE_ON, 0, 17, 21)
        s3 = ShouldBeOn(True, st3)
        self.assertEqual(s1, s3)

        self.assertFalse(s1 and s2)


if __name__ == '__main__':
    unittest.main()

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
