"""Test suite for `thermod.memento` module."""

import copy
import json
import time
import unittest
import jsonschema

from thermod import TimeTable, config
from thermod.memento import memento, transactional
from thermod.tests.timetable import fill_timetable

__updated__ = '2016-02-28'


class MementoTable(TimeTable):
    """Support class for testing memento on thermod.timetable.TimeTable."""
    
    @transactional
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

    def tearDown(self):
        pass

    def testMemento01(self):
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
    
    def testMemento02(self):
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
    
    def testTransactional01(self):
        mt1 = MementoTable()
        mt1.__setstate__(self.timetable.__getstate__())
        mt2 = copy.deepcopy(mt1)
        self.assertEqual(mt1, mt2)
        
        sett = mt1.__getstate__()
        sett[config.json_status] = 'invalid'
        
        with self.assertRaises(jsonschema.ValidationError):
            # set an invalid state, exception raised
            mt2.__setstate__(sett)
        
        # the __setstate__ failed, so the previous state is restored
        self.assertEqual(mt1, mt2)
    
    def testTransactional02(self):
        mt1 = MementoTable()
        mt1.__setstate__(self.timetable.__getstate__())
        mt2 = copy.deepcopy(mt1)
        self.assertEqual(mt1, mt2)
        
        sett = mt1.__getstate__()
        sett[config.json_temperatures][config.json_tmax_str] = 'invalid'
        
        with self.assertRaises(jsonschema.ValidationError):
            # set an invalid state, exception raised
            mt2.__setstate__(sett)
        
        # the __setstate__ failed, so the previous state is restored
        self.assertEqual(mt1, mt2)
    
    def testTransactional03(self):
        mt1 = MementoTable()
        mt1.__setstate__(self.timetable.__getstate__())
        mt2 = copy.deepcopy(mt1)
        self.assertEqual(mt1, mt2)
        
        sett = mt1.__getstate__()
        sett[config.json_timetable] = None  # clearing timetable
        
        with self.assertRaises(jsonschema.ValidationError):
            # set an invalid state, exception raised
            mt2.__setstate__(sett)
        
        # the __setstate__ failed, so the previous state is restored
        self.assertEqual(mt1, mt2)

      
if __name__ == "__main__":
    unittest.main()