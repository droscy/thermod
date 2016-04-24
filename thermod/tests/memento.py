# -*- coding: utf-8 -*-
"""Test suite for `thermod.memento` module."""

import copy
import json
import time
import unittest
import threading
import jsonschema

from thermod import TimeTable, config
from thermod.memento import memento, transactional
from thermod.tests.timetable import fill_timetable

__updated__ = '2016-03-27'


class MementoTable(TimeTable):
    """Support class for testing memento on thermod.timetable.TimeTable."""
    
    @transactional(exclude=['_lock'])
    def __setstate__(self, state):
        """New method without control on errors."""
        
        if not hasattr(self, '_lock'):
            self.__init__()
        
        with self._lock:
            
            # storing new values
            self._status = state[config.json_status]
            self._temperatures = copy.deepcopy(state[config.json_temperatures])
            self._timetable = copy.deepcopy(state[config.json_timetable])
            
            if config.json_differential in state:
                self._differential = state[config.json_differential]
            
            if config.json_grace_time in state:
                self._grace_time = float(state[config.json_grace_time])
            
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

    def tearDown(self):
        pass
    
    
    def test01_memento_status(self):
        tt1 = self.timetable
        tt2 = copy.deepcopy(self.timetable)
        self.assertEqual(tt1, tt2)
        
        # change the status and restore
        restore = memento(tt1)
        tt1.status = config.json_status_off
        self.assertEqual(tt1.status, config.json_status_off)
        self.assertNotEqual(tt1, tt2)  # they now differ
        restore()
        self.assertEqual(tt1, tt2)  # they are equal again
    
    
    def test02_memento_many_days(self):
        tt1 = self.timetable
        tt2 = copy.deepcopy(self.timetable)
        self.assertEqual(tt1, tt2)
        
        data = {'saturday': {'00': [0,0,0,0],     '12': [12,12,12,12],
                             '01': [1,1,1,1],     '13': [13,13,13,13],
                             '02': [2,2,2,2],     '14': [14,14,14,14],
                             '03': [3,3,3,3],     '15': [15,15,15,15],
                             '04': [4,4,4,4],     '16': [16,16,16,16],
                             '05': [5,5,5,5],     '17': [17,17,17,17],
                             '06': [6,6,6,6],     '18': [18,18,18,18],
                             '07': [7,7,7,7],     '19': [19,19,19,19],
                             '08': [8,8,8,8],     '20': [20,20,20,20],
                             '09': [9,9,9,9],     '21': [21,21,21,21],
                             '10': [10,10,10,10], '22': [22,22,22,22],
                             '11': [11,11,11,11], '23': [23,23,23,23]},
                
                '3': {'00': [0,0,0,0],     '12': [12,12,12,12],
                      '01': [1,1,1,1],     '13': [13,13,13,13],
                      '02': [2,2,2,2],     '14': [14,14,14,14],
                      '03': [3,3,3,3],     '15': [15,15,15,15],
                      '04': [4,4,4,4],     '16': [16,16,16,16],
                      '05': [5,5,5,5],     '17': [17,17,17,17],
                      '06': [6,6,6,6],     '18': [18,18,18,18],
                      '07': [7,7,7,7],     '19': [19,19,19,19],
                      '08': [8,8,8,8],     '20': [20,20,20,20],
                      '09': [9,9,9,9],     '21': [21,21,21,21],
                      '10': [10,10,10,10], '22': [22,22,22,22],
                      '11': [11,11,11,11], '23': [23,23,23,23]}}
        
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
        sett[config.json_status] = 'invalid'
        
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
        sett[config.json_temperatures][config.json_tmax_str] = 'invalid'
        
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
            sett[config.json_timetable] = None  # clearing timetable
            
            with self.assertRaises(jsonschema.ValidationError):
                # set an invalid state, exception raised
                mt2.__setstate__(sett)
                
            # the __setstate__ failed, so the previous state is restored
            self.assertEqual(mt1, mt2)
    
    
    def test06_threading(self):
        self.timetable = None  # just to clear and avoid errors
        self.mttable.tmax = 30
        self.mttable.status = config.json_status_tmax
        
        # initial status, the heating should be on
        self.assertTrue(self.mttable.should_the_heating_be_on(20))
        
        # creating updating thread
        thread = threading.Thread(target=self.thread_change_status)
        
        # The lock is acquired, then the thread that changes a parameter is
        # executed. It should wait. An invalid paramether is then stored,
        # the transactional should restore the old values with lock
        # still acquired.
        with self.mttable.lock:
            thread.start()
            self.assertTrue(self.mttable.should_the_heating_be_on(20))
            
            sett = self.mttable.__getstate__()
            sett[config.json_differential] = 'INVALID'
            
            with self.assertRaises(jsonschema.ValidationError):
                # set an invalid state, exception raised
                self.mttable.__setstate__(sett)
            
            self.assertTrue(self.mttable.lock._is_owned())  # still owned
            self.assertTrue(self.mttable.should_the_heating_be_on(20))  # old settings still valid
            
            thread.join(3)  # deadlock, so should exit for timeout
            self.assertTrue(thread.is_alive())  # exit join() for timeout
            self.assertTrue(self.mttable.should_the_heating_be_on(20))  # old settings still valid
        
        # the assert becomes False after the execution of the thread
        thread.join(30)  # no deadlock, timeout only to be sure
        self.assertFalse(thread.is_alive())  # exit join() for lock releasing
        self.assertFalse(self.mttable.should_the_heating_be_on(20))  # new settings of thread
    
    def thread_change_status(self):
        self.assertTrue(self.mttable.should_the_heating_be_on(20))
        
        with self.mttable.lock:
            self.mttable.status = config.json_status_off
            self.assertFalse(self.mttable.should_the_heating_be_on(20))

      
if __name__ == "__main__":
    unittest.main()

# vim: fileencoding=utf-8