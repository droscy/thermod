"""Test suite for `TimeTable` class."""

import os
import copy
import unittest
import tempfile
from unittest import TestCase
from jsonschema import ValidationError
from datetime import datetime, timedelta
from thermod import TimeTable, JsonValueError, config as tconf

__updated__ = '2015-11-19'


def fill_timetable(timetable):
    """Fill a `TimeTable` object with test values."""
    
    timetable.t0 = 5
    timetable.tmin = 17
    timetable.tmax = 21
    
    timetable.differential = 0.5
    timetable.grace_time = 180
    
    t0 = tconf.json_t0_str
    tmin = tconf.json_tmin_str
    tmax = tconf.json_tmax_str
    
    for day in range(7):
        for hour in range(7):
            for quarter in range(4):
                timetable.update(day, hour, quarter, tmin)
        
        for hour in range(7,9):
            for quarter in range(4):
                timetable.update(day, hour, quarter, tmax)
        
        for hour in range(9,16):
            for quarter in range(4):
                timetable.update(day, hour, quarter, tmin)
        
        for hour in range(16,23):
            for quarter in range(4):
                timetable.update(day, hour, quarter, tmax)
        
        hour = 23
        for quarter in range(4):
            timetable.update(day, hour, quarter, t0)
    
    timetable.status = tconf.json_status_auto


class TestTimeTable(TestCase):
    """Test cases for `TimeTable` class."""

    def setUp(self):
        self.timetable = TimeTable()
    
    
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
        with self.assertRaises(ValueError):
            self.timetable.filepath = 'thermod.conf'
            self.timetable.reload()
    
    
    def test_status(self):
        for status in tconf.json_all_statuses:
            self.timetable.status = status
            self.assertEqual(status, self.timetable.status)
        
        status = 'invalid'
        self.assertNotIn(status, tconf.json_all_statuses)
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
        for t in tconf.json_all_temperatures:
            with self.assertRaises(JsonValueError):
                self.timetable.t0 = t
        
        with self.assertRaises(JsonValueError):
                self.timetable.t0 = 'invalid'
    
    
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
        for t in tconf.json_all_temperatures:
            with self.assertRaises(JsonValueError):
                self.timetable.tmin = t
        
        with self.assertRaises(JsonValueError):
                self.timetable.tmin = 'invalid'
    
    
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
        for t in tconf.json_all_temperatures:
            with self.assertRaises(JsonValueError):
                self.timetable.tmax = t
        
        with self.assertRaises(JsonValueError):
                self.timetable.tmax = 'invalid'
    
    
    def test_degrees(self):
        # no main temperatures already set, thus exception
        self.assertRaises(RuntimeError,self.timetable.degrees, 't0')
        
        # set main temperatures
        self.timetable.t0 = 5
        self.timetable.tmin = 17
        self.timetable.tmax = 21
        
        self.assertEqual(self.timetable.degrees(tconf.json_t0_str), 5)
        self.assertEqual(self.timetable.degrees(tconf.json_tmin_str), 17)
        self.assertEqual(self.timetable.degrees(tconf.json_tmax_str), 21)
        
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
        
        # changing the status doesn't make two timetable different
        tt2.status = tconf.json_status_off
        self.assertEqual(self.timetable, tt2)
        self.assertNotEqual(self.timetable.status, tt2.status)
        
        # change other settings and test inequality
        tt.grace_time = 1200
        self.assertNotEqual(self.timetable, tt)
        self.assertNotEqual(self.timetable.grace_time, tt.grace_time)
        
        tt2.update(3,15,0,34)
        self.assertNotEqual(self.timetable, tt2)
    
    
    def test_update(self):
        # TODO this test is not reliable, need improvments or revisitation
        self.assertRaises(JsonValueError, self.timetable.update, 'invalid', 10, 0, tconf.json_tmax_str)
        self.assertRaises(JsonValueError, self.timetable.update, 8, 10, 0, tconf.json_t0_str)
        self.assertRaises(JsonValueError, self.timetable.update, 4, 'invalid', 0, tconf.json_tmin_str)
        self.assertRaises(JsonValueError, self.timetable.update, 4, 23, 5, tconf.json_tmax_str)
        self.assertRaises(JsonValueError, self.timetable.update, 4, 26, 2, tconf.json_tmin_str)
        self.assertRaises(JsonValueError, self.timetable.update, 7, 11, 1, 'invalid')
        self.assertRaises(JsonValueError, self.timetable.update, 4, 11, 'invalid', tconf.json_tmax_str)


    def test_timetable_01(self):  # test t0 status
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = tconf.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = tconf.json_status_t0
        self.timetable.update(day,hour,quarter,tconf.json_tmax_str)
        
        for temp in range(-10,5):
            self.assertTrue(self.timetable.should_the_heating_be_on(temp))
        
        # Not testing temp equal to t0 (5 degrees) because the result
        # depends by both grace time and differential. More on other tests.
        
        for temp in range(6,15):
            self.assertFalse(self.timetable.should_the_heating_be_on(temp))
    
    
    def test_timetable_02(self):  # test tmin status
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = tconf.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = tconf.json_status_tmin
        self.timetable.update(day,hour,quarter,tconf.json_tmax_str)
        
        for temp in range(0,17):
            self.assertTrue(self.timetable.should_the_heating_be_on(temp))
        
        # Not testing temp equal to tmin (17 degrees) because the result
        # depends by both grace time and differential. More on other tests.
        
        for temp in range(18,21):
            self.assertFalse(self.timetable.should_the_heating_be_on(temp))
        
    
    def test_timetable_03(self):  # test tmax status
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = tconf.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = tconf.json_status_tmax
        self.timetable.update(day,hour,quarter,tconf.json_t0_str)
        
        for temp in range(10,21):
            self.assertTrue(self.timetable.should_the_heating_be_on(temp))
        
        # Not testing temp equal to tmax (21 degrees) because the result
        # depends by both grace time and differential. More on other tests.
        
        for temp in range(22,27):
            self.assertFalse(self.timetable.should_the_heating_be_on(temp))
    
    
    def test_timetable_04(self):  # test on/off statuses
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = tconf.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = tconf.json_status_on
        self.timetable.update(day,hour,quarter,tconf.json_tmax_str)
        self.assertTrue(self.timetable.should_the_heating_be_on(3))
        self.assertTrue(self.timetable.should_the_heating_be_on(10))
        self.assertTrue(self.timetable.should_the_heating_be_on(20))
        self.assertTrue(self.timetable.should_the_heating_be_on(22))
        self.assertTrue(self.timetable.should_the_heating_be_on(25))
        self.assertTrue(self.timetable.should_the_heating_be_on(30))
        
        self.timetable.status = tconf.json_status_off
        self.timetable.update(day,hour,quarter,tconf.json_tmax_str)
        self.assertFalse(self.timetable.should_the_heating_be_on(3))
        self.assertFalse(self.timetable.should_the_heating_be_on(10))
        self.assertFalse(self.timetable.should_the_heating_be_on(20))
        self.assertFalse(self.timetable.should_the_heating_be_on(22))
        self.assertFalse(self.timetable.should_the_heating_be_on(25))
        self.assertFalse(self.timetable.should_the_heating_be_on(30))
    
    
    def test_timetable_05(self):  # test auto status
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = tconf.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = tconf.json_status_auto
        
        # current target t0
        self.timetable.update(day,hour,quarter,tconf.json_t0_str)
        self.assertTrue(self.timetable.should_the_heating_be_on(3))
        self.assertFalse(self.timetable.should_the_heating_be_on(10))
        self.assertFalse(self.timetable.should_the_heating_be_on(20))
        self.assertFalse(self.timetable.should_the_heating_be_on(22))
        self.assertFalse(self.timetable.should_the_heating_be_on(25))
        self.assertFalse(self.timetable.should_the_heating_be_on(30))
        
        # current target tmin
        self.timetable.update(day,hour,quarter,tconf.json_tmin_str)
        self.assertTrue(self.timetable.should_the_heating_be_on(3))
        self.assertTrue(self.timetable.should_the_heating_be_on(10))
        self.assertFalse(self.timetable.should_the_heating_be_on(20))
        self.assertFalse(self.timetable.should_the_heating_be_on(22))
        self.assertFalse(self.timetable.should_the_heating_be_on(25))
        self.assertFalse(self.timetable.should_the_heating_be_on(30))
        
        # current target tmax
        self.timetable.update(day,hour,quarter,tconf.json_tmax_str)
        self.assertTrue(self.timetable.should_the_heating_be_on(3))
        self.assertTrue(self.timetable.should_the_heating_be_on(10))
        self.assertTrue(self.timetable.should_the_heating_be_on(20))
        self.assertFalse(self.timetable.should_the_heating_be_on(22))
        self.assertFalse(self.timetable.should_the_heating_be_on(25))
        self.assertFalse(self.timetable.should_the_heating_be_on(30))
        
        # current target manual temperature
        self.timetable.update(day,hour,quarter,27.5)
        self.assertTrue(self.timetable.should_the_heating_be_on(3))
        self.assertTrue(self.timetable.should_the_heating_be_on(10))
        self.assertTrue(self.timetable.should_the_heating_be_on(20))
        self.assertTrue(self.timetable.should_the_heating_be_on(22))
        self.assertTrue(self.timetable.should_the_heating_be_on(25))
        self.assertFalse(self.timetable.should_the_heating_be_on(30))
    
    
    def test_timetable_06(self):
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = tconf.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = tconf.json_status_auto
        self.timetable.update(day,hour,quarter,tconf.json_tmax_str)
        
        # check if the heating should be on
        self.assertTrue(self.timetable.should_the_heating_be_on(19))
        
        # virtually switching on and set internal state
        self.timetable.seton()
        
        # the temperature start increasing
        self.assertTrue(self.timetable.should_the_heating_be_on(20))
        self.assertTrue(self.timetable.should_the_heating_be_on(20.5))
        self.assertTrue(self.timetable.should_the_heating_be_on(21))
        self.assertTrue(self.timetable.should_the_heating_be_on(21.4))
        self.assertFalse(self.timetable.should_the_heating_be_on(21.5))
        
        # virtually switching off and set internal state
        self.timetable.setoff()
        
        # the temperature start decreasing
        self.assertFalse(self.timetable.should_the_heating_be_on(21.4))
        self.assertFalse(self.timetable.should_the_heating_be_on(21))
        self.assertFalse(self.timetable.should_the_heating_be_on(20.6))
        self.assertTrue(self.timetable.should_the_heating_be_on(20.5))
        self.assertTrue(self.timetable.should_the_heating_be_on(20))
    
    
    def test_timetable_07(self):
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = tconf.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = tconf.json_status_auto
        self.timetable.update(day,hour,quarter,tconf.json_tmax_str)
        
        # the heating was on 2 hours ego, more than grace time
        self.timetable._is_on = False
        self.timetable._last_on_time = (now - timedelta(seconds=7200))
        self.assertTrue(self.timetable.should_the_heating_be_on(20.9))
        self.assertFalse(self.timetable.should_the_heating_be_on(21))
        self.assertFalse(self.timetable.should_the_heating_be_on(21.1))
    
    
    def test_timetable_08(self):
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = tconf.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = tconf.json_status_auto
        self.timetable.update(day,hour,quarter,tconf.json_tmax_str)
        self.timetable.grace_time = 3600
        
        # the heating was on 30 minutes ego, less than grace time
        self.timetable._is_on = False
        self.timetable._last_on_time = (now - timedelta(seconds=1800))
        self.assertTrue(self.timetable.should_the_heating_be_on(20.5))
        self.assertFalse(self.timetable.should_the_heating_be_on(20.6))
        self.assertFalse(self.timetable.should_the_heating_be_on(21))
        self.assertFalse(self.timetable.should_the_heating_be_on(21.5))
    
    
    def test_timetable_09(self):
        fill_timetable(self.timetable)
        
        now = datetime.now()
        day = now.strftime('%w')
        hour = tconf.json_format_hour(now.hour)
        quarter = int(now.minute // 15)
        
        self.timetable.status = tconf.json_status_auto
        self.timetable.update(day,hour,quarter,tconf.json_tmax_str)
        self.timetable.grace_time = 60
        self.timetable.seton()
        
        self.assertTrue(self.timetable.should_the_heating_be_on(21.1))
        
        # I simulate the time passing by changing the target temperature
        # next quarter is tmin
        self.timetable.update(day,hour,quarter,tconf.json_tmin_str)
        self.assertFalse(self.timetable.should_the_heating_be_on(21))
        self.timetable.setoff()
        
        # even if next quarter is tmax again, the grace time is not passed and
        # the heating remains off
        self.timetable.update(day,hour,quarter,tconf.json_tmax_str)
        self.assertFalse(self.timetable.should_the_heating_be_on(21))


if __name__ == '__main__':
    unittest.main()
