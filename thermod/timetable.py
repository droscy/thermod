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
__all_temperatures = (__t0_str, __t_min_str, __t_max_str)

__status_on = 'on'
__status_off = 'off'
__status_auto = 'auto'
__all_statuses = (__status_on, __status_off, __status_auto, __t0_str, __t_min_str, __t_max_str)

__json_status = 'status'
__json_temperatures = 'temperatures'
__json_timetable = 'timetable'

__days_name_map = {1:'monday', 2:'tuesday', 3:'wednesday', 4:'thursday', 5:'friday', 6:'saturday', 0:'sunday'} # the same number of %w in strftime()


# internally used to get or set the values of timetable, status and temperatures
__lock = RLock()


# the timetable main variables
__status = None
__timetable = None
__temperatures = None
__json_file_path = None


def __is_valid_temperature(value):
    global __all_temperatures
    return isinstance(value,(int,long,float)) or value in __all_temperatures


def init(filepath):
    """Init the timetable from a json file.
    
    The filepath must be a full path to the json file that
    contains all the informations.
    """
    
    global __lock
    global __json_file_path
    
    with __lock:
        __json_file_path = filepath
        print(filepath)
        reload()


def reload():
    with __lock:
        if __json_file_path is None:
            raise RuntimeError('the timetable is empty, cannot be reloaded, it must be initialized first')
        
        # loading json file
        with open(__json_file_path,'r') as file:
            settings = json.load(file)
            __status = settings[__json_status]
            __temperatures = settings[__json_temperatures]
            __timetable = settings[__json_timetable]
        
        # checking json content
        if __status not in __all_statuses:
            raise ValueError('the status in the timetable is not valid, it must be one of the following values: ' + ', '.join(__all_statuses))
        
        if set(__temperatures.keys()) != set(__all_temperatures):
            raise ValueError('missing or invalid temperature name in timetable, it must contain exactly the following names: ' + ', '.join(__all_temperatures))
        
        if set(__timetable.keys()) != set(__days_name_map.values()):
            raise ValueError('missing or invalid day name in timetable, it must contain every day with these names: ' + ', '.join(__days_name_map.values()))
            
        for (day,hours) in __timetable.items():
            for (hour,quarters) in hours.items():
                if set(map(__is_valid_temperature,quarters)) != set([True]):
                    raise ValueError('invalid temperature in timetable, it must be a number or one of the following values : ' + ', '.join(__all_temperatures))


def save(filepath=None):
    with __lock:
        filepath = filepath or __json_file_path
        if filepath is None:
            raise IOError('destination timetable file not provided')
        
        if __timetable is None:
            raise RuntimeError('the timetable is empty, cannot be saved')
        
        with open(filepath,'w') as file:
            settings = {__json_status: __status,
                        __json_temperatures: __temperatures,
                        __json_timetable: __timetable}
            
            json.dump(settings, file, indent=2)


def update(day,hour,quarter,temperature):
    with __lock:
        if __timetable is None:
            raise RuntimeError('the timetable is empty, cannot be updated')
        
        # get day name
        if day in range(0,6):
            _day = __days_name_map[day]
        elif day in __days_name_map.values():
            _day = day
        else:
            raise ValueError('the provided day name (or number) is not valid')
        
        # check hour validity
        if hour not in range(0,23):
            raise ValueError('the provided hour is not valid, it must be in range 0-23')
        
        # check validity of quarter of an hour
        if quarter not in range(0,3):
            raise ValueError('the provided quarter is not valid, it must be in range 0-3')
        
        # get temperature string value
        if isinstance(temperature,(int,long,float)):
            _temp = format(degrees(temperature),'.1f')
        elif temperature in __all_temperatures:
            _temp = temperature
        else:
            raise ValueError('the provided temperature is not valid, it must be a number or one of the following values : ' + ', '.join(__all_temperatures))
        
        # update timetable
        __timetable[_day][hour][quarter] = _temp


def degrees(temperature):
    """Convert the name of a temperature in its corresponding number value.
    
    If temperature is already a number, it is returned rounded up to one decimal.
    """
    
    value = None
    
    with __lock:
        if isinstance(temperature,(int,long,float)):
            value = temperature;
        elif temperature in __all_temperatures:
            value = __temperatures[temperature]
        else:
            raise ValueError('the provided temperature is not valid, it must be a number or one of the following values : ' + ', '.join(__all_temperatures))
    
    # rounding returned value in order to prevent to many rapid
    # changes between on and off
    return round(float(value),1)


def is_current_target_status_on(current_temperature):
    """Return True if now the heating must be on, False otherwise"""
    
    result = None
    
    with __lock:
        if __timetable is None:
            raise RuntimeError('the timetable is empty, it must be initialized with init() function')
        
        if __status == __status_on:
            result = True
        elif __status == __status_off:
            result = False
        elif __status in __all_temperatures:
            result = (degrees(current_temperature) < degrees(__temperatures[__status]))
        elif __status == __status_auto:
            now = datetime.now()
            target_temperature = degrees(__timetable[__days_name_map[now.strftime('%w')]][now.hour][int(now.minute//15)])
            result = (degrees(current_temperature) < degrees(target_temperature))
    
    return result
