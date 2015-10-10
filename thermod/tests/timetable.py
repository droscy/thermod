'''
Created on 10 ott 2015

@author: simone
'''

import unittest
from thermod import TimeTable
from thermod.config import JsonValueError

__updated__ = '2015-10-10'

# TODO finire di scrivere tutti i TestCase
# TODO trovare un modo per generare il file JSON a runtime dato che i test
# possono essere eseguiti su macchine diverse

class TestTimeTable(unittest.TestCase):

    def setUp(self):
        self.timetable = TimeTable('/home/simone/Documenti/Workspace/thermod/timetable.json')
        pass

    def tearDown(self):
        pass

    def test_filepath_none(self):
        with self.assertRaises(TypeError):
            self.timetable.filepath = None
            self.timetable.reload()
    
    def test_filepath_not_exists(self):
        with self.assertRaises(FileNotFoundError):
            self.timetable.filepath = '/tmp/non_existing_file'
            self.timetable.reload()
            
    def test_filepath_not_json(self):
        with self.assertRaises(JsonValueError):
            self.timetable.filepath = '/home/simone/Documenti/Workspace/thermod/thermod.conf'
            self.timetable.reload()


if __name__ == '__main__':
    unittest.main()
