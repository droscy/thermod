"""Test suite for `thermod.heating` module."""

import os
import logging
import tempfile
import unittest

__updated__ = '2016-01-08'

# TODO completare


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
'''#!/usr/bin/env python
import json

with open(r'%s','w') as f:
    f.write('1')

print(json.dumps({'success': True, 'status': 1, 'error': None}))

exit(0)
''' % self.status_data)
        
        with open(self.switch_off_script, 'w') as file:
            file.write(
'''#!/usr/bin/env python
import json

with open(r'%s','w') as f:
    f.write('0')

print(json.dumps({'success': True, 'status': 0, 'error': None}))

exit(0)
''' % self.status_data)
            
            with open(self.status_script, 'w') as file:
                file.write(
'''#!/usr/bin/env python
import json

with open(r'%s','r') as f:
    status = int(f.read())

print(json.dumps({'success': True, 'status': status, 'error': None}))

exit(0)
''' % self.status_data)
   

    def tearDown(self):
        os.remove(self.switch_on_script)
        os.remove(self.switch_off_script)
        os.remove(self.status_script)
        os.remove(self.status_data)
        #print(self.switch_on_script)
        #print(self.switch_off_script)
        #print(self.status_script)
        #print(self.status_data)
    
    def test_prova(self):
        # TODO
        pass



if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL)
    unittest.main()
