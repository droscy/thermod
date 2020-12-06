# -*- coding: utf-8 -*-
"""Test suite for `thermod.thermometer` module.

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
import logging
import tempfile
import unittest
import numpy
import asyncio

from thermod.common import DEGREE_CELSIUS, DEGREE_FAHRENHEIT
from thermod.thermometer import ScriptThermometer, ThermometerError, \
    celsius2fahrenheit, fahrenheit2celsius, OneWireThermometer, linearfit, \
    ScaleAdapterThermometerDecorator, FakeThermometer

__updated__ = '2020-12-06'


class TestThermometer(unittest.TestCase):
    """Test cases for `thermod.thermometer` module."""

    def setUp(self):
        self.script = os.path.join(tempfile.gettempdir(), 'thermod-test-temperature.py')
        self.temperature_data = os.path.join(tempfile.gettempdir(), 'thermod-test-temperature.data')
        self.w1_data_1 = os.path.join(tempfile.gettempdir(), 'thermod-test-temperature-w1-1.data')
        self.w1_data_2 = os.path.join(tempfile.gettempdir(), 'thermod-test-temperature-w1-2.data')
        self.w1_data_3 = os.path.join(tempfile.gettempdir(), 'thermod-test-temperature-w1-3.data')
        
        with open(self.temperature_data, 'w') as file:
            file.write('20.10')
            
        with open(self.script, 'w') as file:
            file.write(
'''#!/usr/bin/env python3
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
        
        with open(self.w1_data_1, 'w') as file:
            file.write(
'''81 01 4b 46 7f ff 0f 10 71 : crc=71 YES
81 01 4b 46 7f ff 0f 10 71 t=24062
''')
        with open(self.w1_data_2, 'w') as file:
            file.write(
'''80 01 4b 46 7f ff 10 10 c6 : crc=c6 YES
80 01 4b 46 7f ff 10 10 c6 t=24000
''')
        with open(self.w1_data_3, 'w') as file:
            file.write(
'''80 01 4b 46 7f ff 10 10 c6 : crc=c6 YES
80 01 4b 46 7f ff 10 10 c6 t=36000
''')
        
        os.chmod(self.script,0o700)
        self.thermometer = ScriptThermometer(self.script)
        self.w1thermo = OneWireThermometer([self.w1_data_1, self.w1_data_2])
    
    def tearDown(self):
        try:
            os.remove(self.script)
        except FileNotFoundError:
            pass
        
        try:
            os.remove(self.temperature_data)
        except FileNotFoundError:
            pass
        
        try:
            os.remove(self.w1_data_1)
        except FileNotFoundError:
            pass
        
        try:
            os.remove(self.w1_data_2)
        except FileNotFoundError:
            pass
        
        try:
            os.remove(self.w1_data_3)
        except FileNotFoundError:
            pass
    
    def _get_async_temp(self, coro):
        loop = asyncio.get_event_loop()
        temp = loop.run_until_complete(coro)
        return temp
    
    def test_temperature_script(self):
        self.assertAlmostEqual(self._get_async_temp(self.thermometer.temperature), 20.10, delta=0.01)
        
        for t in (10.20, -15.00, 34.34, 17.23, 21.20, 7.76, 22.00):
            with open(self.temperature_data, 'w') as file:
                file.write('{:.2f}'.format(t))
            
            self.assertAlmostEqual(self._get_async_temp(self.thermometer.temperature), t, delta=0.01)
    
    def test_w1_temperatures(self):
        self.assertAlmostEqual(self._get_async_temp(self.w1thermo.temperature), 24.03, delta=0.01)
        
        os.remove(self.w1_data_2)
        self.assertAlmostEqual(self._get_async_temp(self.w1thermo.temperature), 24.06, delta=0.01)
    
    def test_w1_temperatures_outlier(self):
        self.assertAlmostEqual(self._get_async_temp(self.w1thermo.temperature), 24.03, delta=0.01)
        
        self.w1thermo = OneWireThermometer([self.w1_data_1, self.w1_data_2, self.w1_data_3])
        self.assertAlmostEqual(self._get_async_temp(self.w1thermo.temperature), 24.06, delta=0.01)
        
        self.w1thermo = OneWireThermometer([self.w1_data_2, self.w1_data_3])
        self.assertAlmostEqual(self._get_async_temp(self.w1thermo.temperature), 30.00, delta=0.01)
    
    def test_w1_init_error(self):
        with self.assertRaises(TypeError):
            self.w1thermo = OneWireThermometer('string')
        
        with self.assertRaises(ValueError):
            self.w1thermo = OneWireThermometer([])
        
        with self.assertRaises(FileNotFoundError):
            os.remove(self.w1_data_3)
            self.w1thermo = OneWireThermometer([self.w1_data_1, self.w1_data_2, self.w1_data_3])
    
    def test_scale_adapter(self):
        termo = ScaleAdapterThermometerDecorator(self.w1thermo, DEGREE_FAHRENHEIT)
        self.assertAlmostEqual(self._get_async_temp(termo.temperature), 75.26, delta=0.01)
        
        termo = ScaleAdapterThermometerDecorator(FakeThermometer(DEGREE_FAHRENHEIT), DEGREE_CELSIUS)
        self.assertAlmostEqual(self._get_async_temp(termo.temperature), 20.00, delta=0.01)
        
        termo = ScaleAdapterThermometerDecorator(FakeThermometer(), DEGREE_CELSIUS)
        self.assertAlmostEqual(self._get_async_temp(termo.temperature), 20.00, delta=0.01)
    
    def test_conversion_methods(self):
        self.assertAlmostEqual(celsius2fahrenheit(0), 32, delta=0.01)
        self.assertAlmostEqual(fahrenheit2celsius(0), -17.78, delta=0.01)
    
    def test_errors_in_script(self):
        # missing 'temperature' field in JSON output
        with self.assertRaises(ThermometerError):
            with open(self.script, 'w') as file:
                file.write(
'''#!/usr/bin/env python3
import json
print(json.dumps({'error': None}))
exit(0)
''')
            self._get_async_temp(self.thermometer.temperature)
        
        # invalid 'temperature' value in JSON output
        with self.assertRaises(ThermometerError):
            with open(self.script, 'w') as file:
                file.write(
'''#!/usr/bin/env python3
import json
print(json.dumps({'temperature': 'invalid', 'error': None}))
exit(0)
''')
            self._get_async_temp(self.thermometer.temperature)
        
        # null 'temperature' value in JSON output
        with self.assertRaises(ThermometerError):
            with open(self.script, 'w') as file:
                file.write(
'''#!/usr/bin/env python3
import json
print(json.dumps({'temperature': None, 'error': None}))
exit(0)
''')
            self._get_async_temp(self.thermometer.temperature)
        
        # missing 'error' value in JSON output with return code 1
        with self.assertRaises(ThermometerError):
            with open(self.script, 'w') as file:
                file.write(
'''#!/usr/bin/env python3
import json
print(json.dumps({'temperature': None}))
exit(1)
''')
            self._get_async_temp(self.thermometer.temperature)
        
        with self.assertRaises(ThermometerError):
            os.remove(self.temperature_data)
            self._get_async_temp(self.thermometer.temperature)
    
    def test_linear_regression(self):
        """Test the custom computation on linear regression."""
        
        t_ref = (17.4, 18.3, 19.3, 19.7, 20.3, 21.1, 22.1)
        t_raw = (21.0, 22.1, 23.0, 23.4, 23.8, 24.6, 25.9)
        
        f = numpy.poly1d(numpy.polyfit(t_raw, t_ref, 1))
        g = linearfit(t_raw, t_ref)
        
        for t in range(-10, 50):
            self.assertAlmostEqual(f(t), g(t), delta=0.01)


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL)
    unittest.main()

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
