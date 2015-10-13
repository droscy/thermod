"""Test cases for `thermod.TimeTable` class."""

import unittest
import thermod
from json import JSONDecodeError
from jsonschema import ValidationError
from thermod import TimeTable, JsonValueError

__updated__ = '2015-10-13'

# TODO finire di scrivere tutti i TestCase
# TODO trovare un modo per generare il file JSON a runtime dato che i test
# possono essere eseguiti su macchine diverse

class TestTimeTable(unittest.TestCase):

    def setUp(self):
        self.timetable = TimeTable()
    
    
    def tearDown(self):
        pass
    
    
    def test_filepath(self):
        with self.assertRaises(RuntimeError):
            self.timetable.reload()
        
        with self.assertRaises(ValidationError):
            self.timetable.save()
        
        with self.assertRaises(FileNotFoundError):
            self.timetable.filepath = '/tmp/non_existing_file'
            self.timetable.reload()
        
        with self.assertRaises(JSONDecodeError):
            self.timetable.filepath = 'thermod.conf'
            self.timetable.reload()
    
    
    def test_status(self):
        for status in thermod.config.json_all_statuses:
            self.timetable.status = status
            self.assertEqual(status, self.timetable.status)
        
        status = 'invalid'
        self.assertNotIn(status, thermod.config.json_all_statuses)
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
        for t in thermod.config.json_all_temperatures:
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
        for t in thermod.config.json_all_temperatures:
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
        for t in thermod.config.json_all_temperatures:
            with self.assertRaises(JsonValueError):
                self.timetable.tmax = t
        
        with self.assertRaises(JsonValueError):
                self.timetable.tmax = 'invalid'
    
    
    def test_update(self):
        # TODO questo test deve essere completato e migliorato
        self.assertRaises(JsonValueError, self.timetable.update, 'invalid', 10, 0, thermod.config.json_tmax_str)
        self.assertRaises(JsonValueError, self.timetable.update, 8, 10, 0, thermod.config.json_t0_str)
        self.assertRaises(JsonValueError, self.timetable.update, 4, 'invalid', 0, thermod.config.json_tmin_str)
        self.assertRaises(JsonValueError, self.timetable.update, 4, 23, 5, thermod.config.json_tmax_str)
        self.assertRaises(JsonValueError, self.timetable.update, 4, 26, 2, thermod.config.json_tmin_str)
        self.assertRaises(JsonValueError, self.timetable.update, 7, 11, 1, 'invalid')
        self.assertRaises(JsonValueError, self.timetable.update, 4, 11, 'invalid', thermod.config.json_tmax_str)


if __name__ == '__main__':
    unittest.main()
