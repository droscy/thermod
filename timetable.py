# this module is the timetable

import json
from threading import Lock
from datetime import datetime

# TODO mancano tutte le eccezioni

# is internally used to get or set the values of timetable
__lock = Lock()

# the timetable
__timetable = None

def init(file):
    '''Init the timetable from a json file'''
    with __lock, open(file) as json_file:
        __timetable = json.load(json_file)

def check(current_temperature):
    '''Return True if now the heating must be on, False otherwise'''
    result = None
    
    with __lock:
        st = __timetable['status']
        
        if st == 'off':
            result = False
        elif st == 'on':
            result = True
        elif st == 'tmax':
            if 
        # TODO da finire
        now = datetime.now()
        target_temperature = __timetable[now.hour][int(now.minute/15)]
        
        if current_temperature < target_temperature:
            result = True
        else:
            result = False
    
    return result
#