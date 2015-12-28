"""Test suite for `thermod.socket` module."""

import os
import copy
import json
import logging
import tempfile
import unittest
import requests

import thermod.socket as socket
from thermod import TimeTable, ControlThread, config
from thermod.tests.timetable import fill_timetable

__updated__ = '2015-12-28'
__url__ = 'http://localhost:4344/settings'

# TODO cercare di capire come mai ogni tanto i test falliscono per "OSError: [Errno 98] Address already in use"

class TestSocket(unittest.TestCase):
    """Test cases for `thermod.socket` module."""

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
    
    
    def test_post_wrong_messages(self):
        # wrong url
        wrong = requests.post('http://localhost:4344/wrong', {})
        self.assertEqual(wrong.status_code, 404)
        wrong.close()
        
        # wrong value for status
        wrong = requests.post(__url__, {socket.req_settings_status: 'invalid'})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # wrong value (greater then max allowed)
        wrong = requests.post(__url__, {socket.req_settings_differential: 1.1})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # wrong JSON data for days
        wrong = requests.post(__url__, {socket.req_settings_days: '{"monday":["invalid"]}'})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # invalid JSON syntax for days
        wrong = requests.post(__url__, {socket.req_settings_days: '{"monday":["missing quote]}'})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # wrong JSON data for settings
        settings = self.timetable.__getstate__()
        settings[config.json_temperatures][config.json_tmax_str] = 'inf'
        wrong = requests.post(__url__, {socket.req_settings_all: settings})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # invalid JSON syntax for settings
        settings = self.timetable.settings
        wrong = requests.post(__url__, {socket.req_settings_all: settings[0:30]})
        self.assertEqual(wrong.status_code, 400)
        wrong.close()
        
        # check original paramethers
        self.assertAlmostEqual(self.timetable.differential, 0.5, delta=0.01)
        self.assertAlmostEqual(self.timetable.tmax, 21, delta=0.01)
    
    
    def test_post_right_messages(self):
        # single settings
        p = requests.post(__url__, {socket.req_settings_status: config.json_status_off})
        self.assertEqual(p.status_code, 200)
        self.assertEqual(self.timetable.status, config.json_status_off)
        p.close()
        
        # multiple settings
        q = requests.post(__url__, {socket.req_settings_status: config.json_status_tmax,
                                    socket.req_settings_tmax: 32.3,
                                    socket.req_settings_grace_time: 'inf'})
        
        self.assertEqual(q.status_code, 200)
        self.assertEqual(self.timetable.status, config.json_status_tmax)
        self.assertAlmostEqual(self.timetable.tmax, 32.3, delta=0.01)
        self.assertEqual(self.timetable.grace_time, float('inf'))
        q.close()
        
        # some days
        old_set = self.timetable.__getstate__()
        friday = old_set[config.json_timetable][config.json_get_day_name(5)]
        sunday = old_set[config.json_timetable][config.json_get_day_name(7)]
        
        friday['12'][0] = 44
        friday['15'][1] = 45
        sunday['06'][2] = 46
        sunday['07'][3] = 47
        
        r = requests.post(__url__,
            {socket.req_settings_days:
                json.dumps({config.json_get_day_name(5): friday,
                            config.json_get_day_name(7): sunday})})
        
        self.assertEqual(r.status_code, 200)
        new_set = self.timetable.__getstate__()
        new_friday = new_set[config.json_timetable][config.json_get_day_name(5)]
        new_sunday = new_set[config.json_timetable][config.json_get_day_name(7)]
        
        self.assertEqual(new_friday['12'][0], 44)
        self.assertEqual(new_friday['15'][1], 45)
        self.assertEqual(new_sunday['06'][2], 46)
        self.assertEqual(new_sunday['07'][3], 47)
        
        # all settings
        tt2 = copy.deepcopy(self.timetable)
        tt2.status = config.json_status_tmax
        tt2.grace_time = 3600
        tt2.update('thursday', 4, 1, 36.5)
        
        self.assertNotEqual(self.timetable, tt2)  # different before update
        
        s = requests.post(__url__, {socket.req_settings_all: tt2.settings})
        self.assertEqual(s.status_code, 200)
        s.close()
        
        self.assertEqual(self.timetable, tt2)  # equal after update
    
    
    def test_unsupported_http_methods(self):
        pa = requests.patch(__url__, {})
        self.assertEqual(pa.status_code, 501)
        pa.close()
        
        pu = requests.put(__url__, {})
        self.assertEqual(pu.status_code, 501)
        pu.close()
        
        de = requests.delete(__url__)
        self.assertEqual(de.status_code, 501)
        de.close()


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL)
    unittest.main(warnings='ignore')
