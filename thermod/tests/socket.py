"""Test suite for `thermod.socket` module."""

import os
import logging
import tempfile
import unittest
import requests

import thermod.socket as socket
from thermod import TimeTable, ControlThread, config
from thermod.tests.timetable import fill_timetable

__updated__ = '2015-12-23'
__url__ = 'http://localhost:4344/settings'


class TestSocket(unittest.TestCase):

    def setUp(self):
        self.timetable = TimeTable()
        fill_timetable(self.timetable)
        
        self.timetable.filepath = os.path.join(tempfile.gettempdir(), 'timetable.json')
        self.timetable.save()
        
        self.control_socket = ControlThread(self.timetable)
        self.control_socket.start()
   

    def tearDown(self):
        self.control_socket.stop()
        os.remove(self.timetable.filepath)


    def test_get_settings(self):
        # wrong url
        wrong = requests.get('http://localhost:4344/wrong')
        self.assertEqual(wrong.status_code, 404)
        wrong.close()
        
        # right url
        r = requests.get(__url__)
        self.assertEqual(r.status_code, 200)
        settings = r.json()
        r.close()
        
        # check returned settings
        tt = TimeTable()
        tt.__setstate__(settings)
        self.assertEqual(self.timetable, tt)
    
    
    def test_post_settings(self):
        # wrong url
        wrong = requests.post('http://localhost:4344/wrong', {})
        self.assertEqual(wrong.status_code, 404)
        wrong.close()
        
        # wrong value
        wrong = requests.post(__url__, {config.json_status: 'invalid'})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # wrong value
        wrong = requests.post(__url__, {config.json_differential: 1.1})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # wrong JSON data
        wrong = requests.post(__url__, {socket.req_settings_days: '{"monday":["invalid"]}'})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        
        # TODO write more wrong requests to handle the error code
        
        # right url
        p = requests.post(__url__, {config.json_status: config.json_status_off})
        self.assertEqual(p.status_code, 200)
        self.assertEqual(self.timetable.status, config.json_status_off)
        p.close()
        
        p = requests.post(__url__, {config.json_status: config.json_status_tmax,
                                    config.json_tmax_str: 32.3,
                                    config.json_grace_time: 'inf'})
        
        self.assertEqual(p.status_code, 200)
        self.assertEqual(self.timetable.status, config.json_status_tmax)
        self.assertAlmostEqual(self.timetable.tmax, 32.3, delta=0.01)
        self.assertEqual(self.timetable.grace_time, float('inf'))
        p.close()
        
        # TODO write more right requests


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL)
    unittest.main(warnings='ignore')
