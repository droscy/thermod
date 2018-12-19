# -*- coding: utf-8 -*-
"""Test suite for `thermod.cooling` module.

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
from thermod.heating import HeatingError
from thermod.cooling import ScriptCooling

__updated__ = '2018-07-08'


class TestHeating(unittest.TestCase):
    """Test cases for `thermod.heating` module."""

    def setUp(self):
        self.switch_on_script = os.path.join(tempfile.gettempdir(), 'thermod-test-switchon.py')
        self.switch_off_script = os.path.join(tempfile.gettempdir(), 'thermod-test-switchoff.py')
        self.status_script = os.path.join(tempfile.gettempdir(), 'thermod-test-status.py')
        self.status_data = os.path.join(tempfile.gettempdir(), 'thermod-test-status.data')
        
        with open(self.status_data, 'w') as file:
            file.write('0')
        
        with open(self.switch_on_script, 'w') as file:
            file.write(
'''#!/usr/bin/python3
import json

retcode = 0
status = None
error = None

try:
    with open(r'%s','w') as f:
        f.write('1')
    
    status = 1
except Exception as e:
    retcode = 1
    error = str(e)

print(json.dumps({'success': not bool(retcode), 'status': status, 'error': error}))

exit(retcode)
''' % self.status_data)
        
        with open(self.switch_off_script, 'w') as file:
            file.write(
'''#!/usr/bin/python3
import json

retcode = 0
status = None
error = None

try:
    with open(r'%s','w') as f:
        f.write('0')
    
    status = 0
except Exception as e:
    retcode = 1
    error = str(e)

print(json.dumps({'success': not bool(retcode), 'status': status, 'error': error}))

exit(retcode)
''' % self.status_data)
            
        with open(self.status_script, 'w') as file:
            file.write(
'''#!/usr/bin/python3
import json

retcode = 0
status = None
error = None

try:
    with open(r'%s','r') as f:
        status = int(f.read())
except Exception as e:
    retcode = 1
    error = str(e)

print(json.dumps({'success': not bool(retcode), 'status': status, 'error': error}))

exit(retcode)
''' % self.status_data)
        
        os.chmod(self.switch_on_script,0o700)
        os.chmod(self.switch_off_script,0o700)
        os.chmod(self.status_script,0o700)
        
        self.cooling = ScriptCooling(self.switch_on_script,
                                     self.switch_off_script,
                                     self.status_script)
    
    def tearDown(self):
        try:
            os.remove(self.switch_on_script)
        except FileNotFoundError:
            pass
        
        try:
            os.remove(self.switch_off_script)
        except FileNotFoundError:
            pass
        
        try:
            os.remove(self.status_script)
        except FileNotFoundError:
            pass
        
        try:
            os.remove(self.status_data)
        except FileNotFoundError:
            pass
    
    def test_heating(self):
        self.assertEqual(self.cooling.status, 0)
        self.assertEqual(self.cooling.is_on(), False)
        
        self.cooling.switch_on()
        self.assertEqual(self.cooling.status, 1)
        self.assertEqual(self.cooling.is_on(), True)
        
        self.cooling.switch_on()
        self.assertEqual(self.cooling.is_on(), True)
        
        self.cooling.switch_off()
        self.assertEqual(self.cooling.status, 0)
        self.assertEqual(self.cooling.is_on(), False)
    
    def test_errors(self):
        os.remove(self.status_data)
        
        with self.assertRaises(HeatingError):
            self.cooling.status
        
        self.cooling.switch_on()
        self.assertEqual(self.cooling.status, 1)
        
        if os.getuid() != 0:
            # root can write a file even with read only permissions so this
            # test is useless when executed by root
            os.chmod(self.status_data,0o400)
            with self.assertRaises(HeatingError):
                self.cooling.switch_off()
        
        self.assertEqual(self.cooling.is_on(), True)
        self.assertEqual(self.cooling.status, 1)
        os.chmod(self.status_data,0o600)


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL)
    unittest.main()

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
