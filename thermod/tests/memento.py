# -*- coding: utf-8 -*-
"""Test suite for `thermod.memento` module.

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

import copy
import json
import time
import unittest
import threading
import jsonschema

from thermod import TimeTable, timetable, BaseHeating
from thermod.memento import memento, transactional
from thermod.tests.timetable import fill_timetable

__updated__ = '2017-03-04'


class MementoTable(TimeTable):
    """Support class for testing memento on thermod.timetable.TimeTable."""
    
    @transactional(exclude=['_lock'])
    def __setstate__(self, state):
        """New method without control on errors."""
        
        if not hasattr(self, '_lock'):
            self.__init__()
        
        with self._lock:
            
            # storing new values
            self._status = state[timetable.JSON_STATUS]
            self._temperatures = copy.deepcopy(state[timetable.JSON_TEMPERATURES])
            self._timetable = copy.deepcopy(state[timetable.JSON_TIMETABLE])
            
            if timetable.JSON_DIFFERENTIAL in state:
                self._differential = state[timetable.JSON_DIFFERENTIAL]
            
            if timetable.JSON_GRACE_TIME in state:
                self._grace_time = float(state[timetable.JSON_GRACE_TIME])
            
            # validating
            self._has_been_validated = False
            self._validate()
            self._last_update_timestamp = time.time()


class TestMemento(unittest.TestCase):
    """Test cases for `thermod.memento` module.
    
    We test the thermod.memento.transactional() decorator only on
    thermod.timetable.TimeTable.__setstate__() method because any other
    method that entirly changes the state relies on __setstate__().
    """

    def setUp(self):
        self.timetable = TimeTable()
        fill_timetable(self.timetable)
        
        self.mttable = MementoTable()
        fill_timetable(self.mttable)
        
        self.heating = BaseHeating()

    def tearDown(self):
        pass
    
    
    def test01_memento_status(self):
        tt1 = self.timetable
        tt2 = copy.deepcopy(self.timetable)
        self.assertEqual(tt1, tt2)
        
        # change the status and restore
        restore = memento(tt1)
        tt1.status = timetable.JSON_STATUS_OFF
        self.assertEqual(tt1.status, timetable.JSON_STATUS_OFF)
        self.assertNotEqual(tt1, tt2)  # they now differ
        restore()
        self.assertEqual(tt1, tt2)  # they are equal again
    
    
    def test02_memento_many_days(self):
        tt1 = self.timetable
        tt2 = copy.deepcopy(self.timetable)
        self.assertEqual(tt1, tt2)
        
        data = {'saturday': {'h00': [0,0,0,0],     'h12': [12,12,12,12],
                             'h01': [1,1,1,1],     'h13': [13,13,13,13],
                             'h02': [2,2,2,2],     'h14': [14,14,14,14],
                             'h03': [3,3,3,3],     'h15': [15,15,15,15],
                             'h04': [4,4,4,4],     'h16': [16,16,16,16],
                             'h05': [5,5,5,5],     'h17': [17,17,17,17],
                             'h06': [6,6,6,6],     'h18': [18,18,18,18],
                             'h07': [7,7,7,7],     'h19': [19,19,19,19],
                             'h08': [8,8,8,8],     'h20': [20,20,20,20],
                             'h09': [9,9,9,9],     'h21': [21,21,21,21],
                             'h10': [10,10,10,10], 'h22': [22,22,22,22],
                             'h11': [11,11,11,11], 'h23': [23,23,23,23]},
                
                '3': {'h00': [0,0,0,0],     'h12': [12,12,12,12],
                      'h01': [1,1,1,1],     'h13': [13,13,13,13],
                      'h02': [2,2,2,2],     'h14': [14,14,14,14],
                      'h03': [3,3,3,3],     'h15': [15,15,15,15],
                      'h04': [4,4,4,4],     'h16': [16,16,16,16],
                      'h05': [5,5,5,5],     'h17': [17,17,17,17],
                      'h06': [6,6,6,6],     'h18': [18,18,18,18],
                      'h07': [7,7,7,7],     'h19': [19,19,19,19],
                      'h08': [8,8,8,8],     'h20': [20,20,20,20],
                      'h09': [9,9,9,9],     'h21': [21,21,21,21],
                      'h10': [10,10,10,10], 'h22': [22,22,22,22],
                      'h11': [11,11,11,11], 'h23': [23,23,23,23]}}
        
        json_data = json.dumps(data)
        
        # change timetable and restore
        restore = memento(tt1)
        tt1.update_days(json_data)
        self.assertNotEqual(tt1, tt2)  # they now differ
        restore()
        self.assertEqual(tt1, tt2)  # they are equal again
    
    
    def test03_transactional_status(self):
        mt1 = self.mttable
        mt2 = copy.deepcopy(mt1)
        self.assertEqual(mt1, mt2)
        
        sett = mt1.__getstate__()
        sett[timetable.JSON_STATUS] = 'invalid'
        
        with self.assertRaises(jsonschema.ValidationError):
            # set an invalid state, exception raised
            mt2.__setstate__(sett)
        
        # the __setstate__ failed, so the previous state is restored
        self.assertEqual(mt1, mt2)
    
    
    def test04_transactional_temperature(self):
        mt1 = self.mttable
        mt2 = copy.deepcopy(mt1)
        self.assertEqual(mt1, mt2)
        
        sett = mt1.__getstate__()
        sett[timetable.JSON_TEMPERATURES][timetable.JSON_TMAX_STR] = 'invalid'
        
        with self.assertRaises(jsonschema.ValidationError):
            # set an invalid state, exception raised
            mt2.__setstate__(sett)
        
        # the __setstate__ failed, so the previous state is restored
        self.assertEqual(mt1, mt2)
    
    
    def test05_transactional_all_timetable(self):
        mt1 = self.mttable
        mt2 = copy.deepcopy(mt1)
        self.assertEqual(mt1, mt2)
        
        with mt1.lock:
            sett = mt1.__getstate__()
            sett[timetable.JSON_TIMETABLE] = None  # clearing timetable
            
            with self.assertRaises(jsonschema.ValidationError):
                # set an invalid state, exception raised
                mt2.__setstate__(sett)
                
            # the __setstate__ failed, so the previous state is restored
            self.assertEqual(mt1, mt2)
    
    
    def test06_threading(self):
        self.timetable = None  # just to clear and avoid errors
        self.mttable.tmax = 30
        self.mttable.status = timetable.JSON_STATUS_TMAX
        
        # initial status, the heating should be on
        self.assertTrue(self.mttable.should_the_heating_be_on(20, self.heating.status, self.heating.switch_off_time))
        
        # creating updating thread
        thread = threading.Thread(target=self.thread_change_status)
        
        # The lock is acquired, then the thread that changes a parameter is
        # executed. It should wait. An invalid paramether is then stored,
        # the transactional should restore the old values with lock
        # still acquired.
        with self.mttable.lock:
            thread.start()
            self.assertTrue(self.mttable.should_the_heating_be_on(20, self.heating.status, self.heating.switch_off_time))
            
            sett = self.mttable.__getstate__()
            sett[timetable.JSON_DIFFERENTIAL] = 'INVALID'
            
            with self.assertRaises(jsonschema.ValidationError):
                # set an invalid state, exception raised
                self.mttable.__setstate__(sett)
            
            self.assertTrue(self.mttable.lock._is_owned())  # still owned
            self.assertTrue(self.mttable.should_the_heating_be_on(20, self.heating.status, self.heating.switch_off_time))  # old settings still valid
            
            thread.join(3)  # deadlock, so should exit for timeout
            self.assertTrue(thread.is_alive())  # exit join() for timeout
            self.assertTrue(self.mttable.should_the_heating_be_on(20, self.heating.status, self.heating.switch_off_time))  # old settings still valid
        
        # the assert becomes False after the execution of the thread
        thread.join(30)  # no deadlock, timeout only to be sure
        self.assertFalse(thread.is_alive())  # exit join() for lock releasing
        self.assertFalse(self.mttable.should_the_heating_be_on(20, self.heating.status, self.heating.switch_off_time))  # new settings of thread
    
    def thread_change_status(self):
        self.assertTrue(self.mttable.should_the_heating_be_on(20, self.heating.status, self.heating.switch_off_time))
        
        with self.mttable.lock:
            self.mttable.status = timetable.JSON_STATUS_OFF
            self.assertFalse(self.mttable.should_the_heating_be_on(20, self.heating.status, self.heating.switch_off_time))

      
if __name__ == "__main__":
    unittest.main()

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab