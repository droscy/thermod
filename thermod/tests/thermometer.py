"""Test suite for `thermod.thermometer` module."""

import os
import logging
import tempfile
import unittest
from thermod.thermometer import ScriptThermometer, ThermometerError, celsius2fahrenheit, fahrenheit2celsius

__updated__ = '2016-02-10'


class TestThermometer(unittest.TestCase):
    """Test cases for `thermod.thermometer` module."""

    def setUp(self):
        self.script = os.path.join(tempfile.gettempdir(), 'thermod-test-temperature.py')
        self.temperature_data = os.path.join(tempfile.gettempdir(), 'thermod-test-temperature.data')
        
        with open(self.temperature_data, 'w') as file:
            file.write('20.10')
            
        with open(self.script, 'w') as file:
            file.write(
'''#!/usr/bin/env python
import json

retcode = 0
t = None
error = None

try:
    with open(r'%s','r') as f:
        t = float(f.read())
except Exception as e:
    retcode = 1
    error = str(e)

print(json.dumps({'temperature': t, 'error': error}))

exit(retcode)
''' % self.temperature_data)
        
        os.chmod(self.script,0o700)
        self.thermometer = ScriptThermometer(self.script)
    
    def tearDown(self):
        try:
            os.remove(self.script)
        except FileNotFoundError:
            pass
        
        try:
            os.remove(self.temperature_data)
        except FileNotFoundError:
            pass
    
    def test_temperature_script(self):
        self.assertAlmostEqual(self.thermometer.temperature, 20.10, delta=0.01)
        
        for t in (10.20, -15.00, 34.34, 17.23, 21.20, 7.76, 22.00):
            with open(self.temperature_data, 'w') as file:
                file.write('{:.2f}'.format(t))
            
            self.assertAlmostEqual(self.thermometer.temperature, t, delta=0.01)
    
    def test_conversion_methods(self):
        self.assertAlmostEqual(celsius2fahrenheit(0), 32, delta=0.01)
        self.assertAlmostEqual(fahrenheit2celsius(0), -17.78, delta=0.01)
        
        self.assertAlmostEqual(self.thermometer.temperature, 20.10, delta=0.01)
        self.assertAlmostEqual(self.thermometer.to_celsius(), 20.10, delta=0.01)
        self.assertAlmostEqual(self.thermometer.to_fahrenheit(), 68.18, delta=0.01)
    
    def test_errors_in_script(self):
        # missing 'temperature' field in JSON output
        with self.assertRaises(ThermometerError):
            with open(self.script, 'w') as file:
                file.write(
'''#!/usr/bin/env python
import json
print(json.dumps({'error': None}))
exit(0)
''')
            self.thermometer.temperature
        
        # invalid 'temperature' value in JSON output
        with self.assertRaises(ThermometerError):
            with open(self.script, 'w') as file:
                file.write(
'''#!/usr/bin/env python
import json
print(json.dumps({'temperature': 'invalid', 'error': None}))
exit(0)
''')
            self.thermometer.temperature
        
        # null 'temperature' value in JSON output
        with self.assertRaises(ThermometerError):
            with open(self.script, 'w') as file:
                file.write(
'''#!/usr/bin/env python
import json
print(json.dumps({'temperature': None, 'error': None}))
exit(0)
''')
            self.thermometer.temperature
        
        # missing 'error' value in JSON output with return code 1
        with self.assertRaises(ThermometerError):
            with open(self.script, 'w') as file:
                file.write(
'''#!/usr/bin/env python
import json
print(json.dumps({'temperature': None}))
exit(1)
''')
            self.thermometer.temperature
        
        with self.assertRaises(ThermometerError):
            os.remove(self.temperature_data)
            self.thermometer.temperature


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL)
    unittest.main()