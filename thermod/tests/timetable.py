# -*- coding: utf-8 -*-
"""Test suite for `TimeTable` class.

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
#import json
import time
import locale
import unittest
import tempfile
import threading
from jsonschema import ValidationError
#from json.decoder import JSONDecodeError
from datetime import datetime, timedelta
from thermod import timetable, TimeTable, ShouldBeOn, JsonValueError, utils, BaseHeating, ThermodStatus

__updated__ = '2017-10-19'


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
    
    tt.status = timetable.JSON_STATUS_AUTO


class TestTimeTable(unittest.TestCase):
    """Test cases for `TimeTable` class."""

    def setUp(self):
        self.timetable = TimeTable()
        self.heating = BaseHeating()
    
    
    def tearDown(self):
        pass
    
    
    def test_filepath(self):
        # empty tiletable
        self.assertRaises(RuntimeError,self.timetable.reload)
        self.assertRaises(RuntimeError,self.timetable.save)
        
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
    
    
    def test_status(self):
        for status in timetable.JSON_ALL_STATUSES:
            self.timetable.status = status
            self.assertEqual(status, self.timetable.status)
        
        status = 'invalid'
        self.assertNotIn(status, timetable.JSON_ALL_STATUSES)
        with self.assertRaises(JsonValueError):
            self.timetable.status = status
    
    
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
        self.assertEqual(self.timetable.status, tt1.status)
        
        tt1.save(filepath2)
        tt2 = TimeTable()
        tt2.filepath = filepath2
        tt2.reload()
        self.assertEqual(self.timetable, tt2)
        self.assertEqual(self.timetable.status, tt2.status)
        
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
        self.assertEqual(self.timetable.status, tt.status)
        
        # test copy operators
        tt2 = copy.deepcopy(self.timetable)
        self.assertEqual(self.timetable, tt2)
        self.assertEqual(self.timetable.status, tt2.status)
        
        # changing the status makes two timetable different
        tt2.status = timetable.JSON_STATUS_OFF
        self.assertNotEqual(self.timetable, tt2)
        self.assertNotEqual(self.timetable.status, tt2.status)
        
        # change other settings and test inequality
        tt.grace_time = 1200
        self.assertNotEqual(self.timetable, tt)
        self.assertNotEqual(self.timetable.grace_time, tt.grace_time)
        
        tt2.update(3,15,0,34)
        self.assertNotEqual(self.timetable, tt2)
    
    
    def test_update(self):
        # TODO this test is not reliable, need improvments or revisitation
        self.assertRaises(JsonValueError, self.timetable.update, 'invalid', 10, 0, timetable.JSON_TMAX_STR)
        self.assertRaises(JsonValueError, self.timetable.update, 8, 10, 0, timetable.JSON_T0_STR)
        self.assertRaises(JsonValueError, self.timetable.update, 4, 'invalid', 0, timetable.JSON_TMIN_STR)
        self.assertRaises(JsonValueError, self.timetable.update, 4, 23, 5, timetable.JSON_TMAX_STR)
        self.assertRaises(JsonValueError, self.timetable.update, 4, 26, 2, timetable.JSON_TMIN_STR)
        self.assertRaises(JsonValueError, self.timetable.update, 7, 11, 1, 'invalid')
        self.assertRaises(JsonValueError, self.timetable.update, 4, 11, 'invalid', timetable.JSON_TMAX_STR)
    
    
    #def test_update_day(self):
    #    fill_timetable(self.timetable)
    #    
    #    data = {'saturday': {'h00': [0,0,0,0],     'h12': [12,12,12,12],
    #                         'h01': [1,1,1,1],     'h13': [13,13,13,13],
    #                         'h02': [2,2,2,2],     'h14': [14,14,14,14],
    #                         'h03': [3,3,3,3],     'h15': [15,15,15,15],
    #                         'h04': [4,4,4,4],     'h16': [16,16,16,16],
    #                         'h05': [5,5,5,5],     'h17': [17,17,17,17],
    #                         'h06': [6,6,6,6],     'h18': [18,18,18,18],
    #                         'h07': [7,7,7,7],     'h19': [19,19,19,19],
    #                         'h08': [8,8,8,8],     'h20': [20,20,20,20],
    #                         'h09': [9,9,9,9],     'h21': [21,21,21,21],
    #                         'h10': [10,10,10,10], 'h22': [22,22,22,22],
    #                         'h11': [11,11,11,11], 'h23': [23,23,23,23]},
    #            
    #            '3': {'h00': [0,0,0,0],     'h12': [12,12,12,12],
    #                  'h01': [1,1,1,1],     'h13': [13,13,13,13],
    #                  'h02': [2,2,2,2],     'h14': [14,14,14,14],
    #                  'h03': [3,3,3,3],     'h15': [15,15,15,15],
    #                  'h04': [4,4,4,4],     'h16': [16,16,16,16],
    #                  'h05': [5,5,5,5],     'h17': [17,17,17,17],
    #                  'h06': [6,6,6,6],     'h18': [18,18,18,18],
    #                  'h07': [7,7,7,7],     'h19': [19,19,19,19],
    #                  'h08': [8,8,8,8],     'h20': [20,20,20,20],
    #                  'h09': [9,9,9,9],     'h21': [21,21,21,21],
    #                  'h10': [10,10,10,10], 'h22': [22,22,22,22],
    #                  'h11': [11,11,11,11], 'h23': [23,23,23,23]}}
    #    
    #    json_data = json.dumps(data)
    #    self.timetable.update_days(json_data)
    #    
    #    day6 = utils.json_get_day_name(6)
    #    day3 = utils.json_get_day_name(3)
    #    state = self.timetable.__getstate__()
    #    
    #    for h in range(24):
    #        hour = utils.json_format_hour(h)
    #        t1_6 = utils.temperature_to_float(state[timetable.JSON_TIMETABLE][day6][hour])
    #        t1_3 = utils.temperature_to_float(state[timetable.JSON_TIMETABLE][day3][hour])
    #        t2 = utils.temperature_to_float(h)
    #        self.assertEqual(t1_6, t2)
    #        self.assertEqual(t1_3, t2)
    #    
    #    self.assertRaises(ValidationError, self.timetable.update_days, json.dumps({'monday': {'00': [0,0,0]}}))
    #    self.assertRaises(JsonValueError, self.timetable.update_days, json.dumps({'00': data['saturday']}))
    #    self.assertRaises(JsonValueError, self.timetable.update_days, json.dumps(data['saturday']['h15']))
    #    self.assertRaises(JSONDecodeError, self.timetable.update_days, '{invalid}')
    #    self.assertRaises(TypeError, self.timetable.update_days, data)
    
    
    def test_locale(self):
        # setlocale doesn't work on Windows
        if os.name == 'posix':
            locale.setlocale(locale.LC_ALL,'it_IT.utf8')
            
            fill_timetable(self.timetable)
            
            self.assertIsNone(self.timetable.update('Lun',10,1,30))
            self.assertIsNone(self.timetable.update('mer',11,2,20))
            settings = self.timetable.__getstate__()
            
            day = utils.json_get_day_name(1)
            hour = utils.json_format_hour(10)
            quarter = 1
            t1 = utils.temperature_to_float(settings[timetable.JSON_TIMETABLE][day][hour][quarter])
            t2 = utils.temperature_to_float(30)
            self.assertEqual(t1, t2)
    
            day = utils.json_get_day_name(3)
            hour = utils.json_format_hour(11)
            quarter = 2
            t1 = utils.temperature_to_float(settings[timetable.JSON_TIMETABLE][day][hour][quarter])
            t2 = utils.temperature_to_float(20)
            self.assertEqual(t1, t2)
    
    
    def test_timetable_01(self):  # test t0 status
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = utils.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = timetable.JSON_STATUS_T0
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        
        for temp in range(-10,5):
            self.assertTrue(self.timetable.should_the_heating_be_on(temp, self.heating.status))
        
        # Not testing temp equal to t0 (5 degrees) because the result
        # depends by both grace time and differential. More on other tests.
        
        for temp in range(6,15):
            self.assertFalse(self.timetable.should_the_heating_be_on(temp, self.heating.status))
    
    
    def test_timetable_02(self):  # test tmin status
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = utils.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = timetable.JSON_STATUS_TMIN
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        
        for temp in range(0,17):
            self.assertTrue(self.timetable.should_the_heating_be_on(temp, self.heating.status))
        
        # Not testing temp equal to tmin (17 degrees) because the result
        # depends by both grace time and differential. More on other tests.
        
        for temp in range(18,21):
            self.assertFalse(self.timetable.should_the_heating_be_on(temp, self.heating.status))
        
    
    def test_timetable_03(self):  # test tmax status
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = utils.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = timetable.JSON_STATUS_TMAX
        self.timetable.update(day,hour,quarter,timetable.JSON_T0_STR)
        
        for temp in range(10,21):
            self.assertTrue(self.timetable.should_the_heating_be_on(temp, self.heating.status))
        
        # Not testing temp equal to tmax (21 degrees) because the result
        # depends by both grace time and differential. More on other tests.
        
        for temp in range(22,27):
            self.assertFalse(self.timetable.should_the_heating_be_on(temp, self.heating.status))
    
    
    def test_timetable_04(self):  # test on/off statuses
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = utils.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = timetable.JSON_STATUS_ON
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        self.assertTrue(self.timetable.should_the_heating_be_on(3, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(10, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(20, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(22, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(25, self.heating.status))
        self.assertTrue(self.timetable.should_the_heating_be_on(30, self.heating.status))
        
        self.timetable.status = timetable.JSON_STATUS_OFF
        self.timetable.update(day,hour,quarter,timetable.JSON_TMAX_STR)
        self.assertFalse(self.timetable.should_the_heating_be_on(3, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(10, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(20, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(22, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(25, self.heating.status))
        self.assertFalse(self.timetable.should_the_heating_be_on(30, self.heating.status))
    
    
    def test_timetable_05(self):  # test auto status
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = utils.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = timetable.JSON_STATUS_AUTO
        
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
        hour = utils.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = timetable.JSON_STATUS_AUTO
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
    
    
    def test_timetable_07(self):
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = utils.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = timetable.JSON_STATUS_AUTO
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
        hour = utils.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = timetable.JSON_STATUS_AUTO
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
        hour = utils.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = timetable.JSON_STATUS_AUTO
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
        hour = utils.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = timetable.JSON_STATUS_AUTO
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
        hour = utils.json_format_hour(time.hour)
        quarter = int(time.minute // 15)
        
        self.assertAlmostEqual(self.timetable.target_temperature(time), self.timetable.tmax, delta=0.01)
        t = 45.0
        self.timetable.update(day, hour, quarter, t)
        self.assertAlmostEqual(self.timetable.target_temperature(time), t, delta=0.01)
        
        self.assertAlmostEqual(self.timetable.target_temperature(datetime(2016,2,10,9,34,0)), self.timetable.tmin, delta=0.01)
        self.assertAlmostEqual(self.timetable.target_temperature(datetime(2016,2,10,23,34,0)), self.timetable.t0, delta=0.01)
        
        self.timetable.status = timetable.JSON_STATUS_ON
        self.assertEqual(self.timetable.target_temperature(time), None)
        
        self.timetable.status = timetable.JSON_STATUS_OFF
        self.assertEqual(self.timetable.target_temperature(time), None)
        
        self.timetable.status = timetable.JSON_STATUS_TMAX
        self.assertAlmostEqual(self.timetable.target_temperature(time), self.timetable.tmax, delta=0.01)
        
        self.timetable.status = timetable.JSON_STATUS_TMIN
        self.assertAlmostEqual(self.timetable.target_temperature(time), self.timetable.tmin, delta=0.01)
        
        self.timetable.status = timetable.JSON_STATUS_T0
        self.assertAlmostEqual(self.timetable.target_temperature(time), self.timetable.t0, delta=0.01)
    
    
    # TODO write more concurrent tests
    def test_threading_01(self):
        fill_timetable(self.timetable)
        
        self.timetable.tmax = 30
        self.timetable.status = timetable.JSON_STATUS_TMAX
        
        # initial status, the heating should be on
        self.assertTrue(self.timetable.should_the_heating_be_on(20, self.heating.status))
        
        # creating main lock
        lock = threading.Condition()
        
        # creating updating thread
        thread = threading.Thread(target=self.thread_change_status, args=(lock,))
        
        # the lock is acquired, then the thread that changes a parameter is
        # executed and the assert is checked again, if the lock works the
        # assert is still True
        with lock:
            thread.start()
            self.assertTrue(self.timetable.should_the_heating_be_on(20, self.heating.status))
        
        # the assert become False after the execution of the thread
        thread.join()
        self.assertFalse(self.timetable.should_the_heating_be_on(20, self.heating.status))
    
    def thread_change_status(self, lock):
        self.assertTrue(self.timetable.should_the_heating_be_on(20, self.heating.status))
        
        with lock:
            self.timetable.status = timetable.JSON_STATUS_OFF
            self.assertFalse(self.timetable.should_the_heating_be_on(20, self.heating.status))

    def test_should_be_on(self):
        s1 = ShouldBeOn(True)
        self.assertTrue(s1)
        
        st2 = ThermodStatus(time.time(), timetable.JSON_STATUS_AUTO, 1, 5, 10)
        s2 = ShouldBeOn(False, st2)
        self.assertFalse(s2)
        
        st3 = ThermodStatus(time.time(), timetable.JSON_STATUS_ON, 0, 17, 21)
        s3 = ShouldBeOn(True, st3)
        self.assertEqual(s1, s3)

        self.assertFalse(s1 and s2)


if __name__ == '__main__':
    unittest.main()

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
