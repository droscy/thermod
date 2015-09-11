# this module is the timetable

import json
from threading import RLock
from datetime import datetime

# TODO mancano tutte le eccezioni
# TODO c'è da scrivere come aggiornare a runtime e quindi salvare su json le modifiche

# thermod name convention (from json file)
__t0_str = 't0'
__t_min_str = 'tmin'
__t_max_str = 'tmax'

__status_on = 'on'
__status_off = 'off'
__status_auto = 'auto'

__json_status = 'status'
__json_temperatures = 'temperatures'
__json_days = 'days'

__days_name_map = {1:'monday', 2:'tuesday', 3:'wednesday', 4:'thursday', 5:'friday', 6:'saturday', 0:'sunday'} # the same number of %w in strftime()


# internally used to get or set the values of timetable, status and temperatures
__lock = RLock()


# the timetable main variables
__status = None
__timetable = None
__temperatures = None
__json_file_path = None


def init(filepath):
    """Init the timetable from a json file.
    
    The filepath must be a full path to the json file that
    contains all the informations.
    """
    
    with __lock:
        __json_file_path = path
        reload()


def reload():
    with __lock:
        if __json_file_path is None:
            raise RuntimeError('the timetable is empty, it must be initialized with init() function')
    
        with open(__json_file_path) as file:
            settings = json.load(file)
            __status = settings[__json_status]
            __temperatures = settings[__json_temperatures]
            __timetable = settings[__json_days]


def name2degrees(temp):
    """Convert the name of a temperature in its corresponding number value.
    
    If temp is already a number, it is returned.
    """
    
    result = None
    
    with __lock:
        if isinstance(temp,(int,long,float)):
            result = temp;
        elif temp in (__t0_str,__t_min_str,__t_max_str)
            result = __temperatures[temp]
        else:
            raise ValueError('the timetable contains an invalid temperature name')
    
    return result


# TODO si potrebbe far ritornare una stringa con __status_on oppure __status_off, no perché dall'esterno le variabili __ non vanno usate
def to_be_switched_on(current_temperature):
    """Return True if now the heating must be on, False otherwise"""
    
    result = None
    
    with __lock:
        if __timetable is None:
            raise RuntimeError('the timetable is empty, it must be initialized with init() function')
        
        if __status == __status_on:
            result = True
        elif __status == __status_off:
            result = False
        elif __status in (__t0_str,__t_min_str,__t_max_str):
            if round(current_temperature,1) < round(__temperatures[__status],1): # TODO si arrotonda per evitare troppe fluttuazioni acceso/spento 
                result = True
            else:
                result = False
        elif __status == __status_auto:
            now = datetime.now()
            target_temperature = name2degrees(__timetable[__days_name_map[now.strftime('%w')]][now.hour][int(now.minute//15)])

            if round(current_temperature,1) < round(target_temperature,1):
                result = True
            else:
                result = False
    
    return result
