# this module is the timetable

import json
import logging
from threading import RLock
from datetime import datetime
from thermod import config

# TODO mancano tutte le eccezioni
# TODO c'è da scrivere come aggiornare a runtime e quindi salvare su json le modifiche
# TODO write unit-test

__updated__ = '2015-09-23'

logger = logging.getLogger('thermod.timetable')

class TimeTable():
    
    def __init__(self, filepath):
        """Init the timetable from a json file.

        The filepath must be a full path to the json file that
        contains all the informations to setup the timetable.
        """
        
        logger.debug('initializing timetable')

        self.__status = None
        self.__timetable = None
        self.__temperatures = None

        self.__lock = RLock()

        self.filepath = filepath
        self.reload()
    
    
    def reload(self):
        # TODO questa docstring è da rivedere
        # TODO bisogna gestire la situazione in cui self.filepath non sia una stringa o che il file non si possa leggere
        """Reload the timetable from the same json file.
        
        The json file is the same provided in __init__() method, thus
        if a different file is needed, set self.filepath to the full
        path before calling this method.
        
        If the json file is invalid (or self.filepath is not a string) an exception is raised and the
        internal settings of the object remain untouched.
        """
        logger.debug('(re)loading timetable from json file "{}"'.format(self.filepath))
        
        with self.__lock:
            logger.debug('lock acquired to (re)load timetable')
            
            # loading json file
            logger.debug('opening json file')
            with open(self.filepath, 'r') as file:
                # TODO bisogna anche controllare che le voci principali (status, temperature e timetable)
                # ci siano nel file json
                settings = json.load(file)
                status = settings[config.json_status]
                temperatures = settings[config.json_temperatures]
                timetable = settings[config.json_timetable]
                logger.debug('json file loaded')
            
            # checking json content
            logger.debug('checking json content')
            
            if status not in config.json_all_statuses:
                logger.debug('invalid status in json file: {}'.format(status))
                raise ValueError('invalid status in timetable file, the status must be one of the following values: ' + ', '.join(config.json_all_statuses))
            
            _provided_temp = set(temperatures.keys())
            _required_temp = set(config.json_all_temperatures)
            if (_provided_temp & _required_temp) != _required_temp:
                _missing_temp = _required_temp - (_provided_temp & _required_temp)
                logger.debug('missing required temperature in json file: {}'.format(_missing_temp))
                raise ValueError('missing required temperature in timetable file, the file must contain exactly the following temperatures: ' + ', '.join(config.json_all_temperatures))
            
            for (name,value) in temperatures.items():
                # main temperatures must be numbers, so check the validity and
                # exclude from valid values the string defined in config.json_all_temperatures
                if not config.is_valid_temperature(value) or value in config.json_all_temperatures:
                    logger.debug('invalid temperature value for "{}" in json file: {}'.format(name,value))
                    raise ValueError('invalid temperature value for "{}" in timetable file, main temperatures must be numbers'.format(name))
            
            _provided_days = set(timetable.keys())
            _required_days = set(config.json_days_name_map.values())
            if (_provided_days & _required_days) != _required_days:
                _missing_days = _required_days - (_provided_days & _required_days)
                logger.debug('missing required day name in json file: {}'.format(_missing_days))
                raise ValueError('missing required day name in timetable file, the file must contain exactly these days: ' + ', '.join(config.json_days_name_map.values()))
            
            for day in timetable.keys():
                for hour in range(24):
                    hour_str = format(hour,'02d')
                    try:
                        for quarter in range(4):
                            # if the array day[hour_str] contains less than 4 elements
                            # a KeyError exception is automatically raised, so the 'except'
                            # section manages both missing and invalid temperature
                            if not config.is_valid_temperature(timetable[day][hour_str][quarter]):
                                logger.debug('invalid temperature in json file for day "{}", hour "{}" and quarter "{}"'.format(day,hour_str,quarter))
                                raise ValueError()
                    except:
                        logger.debug('invalid or missing temperature in json file for day "{}" and hour "{}"'.format(day,hour_str))
                        raise ValueError('invalid or missing temperature in timetable file for day "{}" and hour "{}", '
                                         'the temperature must be a number or one of the following values: '.format(day,hour_str) + ', '.join(config.json_all_temperatures))
            
            logger.debug('json content valid, storing internal variables')
            
            self.__status = status
            self.__temperatures = temperatures
            self.__timetable = timetable
            
            logger.debug('current status: {}'.format(self.__status))
            logger.debug('temperatures: t0={t0}, tmin={tmin}, tmax={tmax}'.format(**self.__temperatures))
        
        logger.debug('timetable (re)loaded')
    
    
    def save(self, filepath=None):
        """Save the current timetable to json file.
        
        Save the current configuration of the timetable to a json file
        pointed by filepath (full path to file). I filepath is None
        the settings are saved to the json file provided during the
        creation of the object (self.filepath).
        """
        
        logger.debug('saving timetable to file')
        
        with self.__lock:
            logger.debug('lock acquired to save timetable')
            
            if self.__timetable is None:
                logger.debug('empty timetable, cannot be saved')
                raise RuntimeError('the timetable is empty, cannot be saved')
            
            with open(filepath or self.__json_file_path, 'w') as file:
                logger.debug('saving timetable to json file {}'.format(filepath))
                
                settings = {config.json_status: self.__status,
                            config.json_temperatures: self.__temperatures,
                            config.json_timetable: self.__timetable}
                
                json.dump(settings, file, indent=2, sort_keys=True)
        
        logger.debug('timetable saved')
    
    
    def update(self, day, hour, quarter, temperature):
        logger.debug('updating timetable: day "{}", hour "{}", quarter "{}", temperature "{}"'.format(day, hour, quarter, temperature))
        
        with self.__lock:
            logger.debug('lock acquired to update timetable')
            
            if self.__timetable is None:
                logger.debug('empty timetable, cannot be updated')
                raise RuntimeError('the timetable is empty, cannot be updated')

            # get day name
            logger.debug('retriving day name')
            if day in config.json_days_name_map.keys():
                _day = config.json_days_name_map[day]
            elif day in config.json_days_name_map.values():
                _day = day
            else:
                logger.debug('invalid day name or number: {}'.format(day))
                raise ValueError('the provided day name or number ({}) is not valid'.format(day))

            # check hour validity
            logger.debug('checking and formatting hour')
            _hour = config.json_format_hour(hour)

            # check validity of quarter of an hour
            logger.debug('checking validity of quarter')
            if int(float(quarter)) in range(4):
                _quarter = int(float(quarter))
            else:
                logger.debug('invalid quarter: {}'.format(quarter))
                raise ValueError('the provided quarter is not valid ({}), it must be in range 0-3'.format(quarter))

            # update timetable
            self.__timetable[_day][_hour][_quarter] = config.json_format_temperature(temperature)
        
        logger.debug('timetable updated: day "{}", hour "{}", quarter "{}", temperature "{}"'.format(_day, _hour, _quarter, self.__timetable[_day][_hour][_quarter]))
    
    
    def degrees(self, temperature):
        """Convert the name of a temperature in its corresponding number value.
        
        If temperature is already a number, the number itself is returned.
        """
        
        logger.debug('converting temperature name to degrees')
        
        value = None
        
        with self.__lock:
            logger.debug('lock acquired to convert temperature name')
            
            _temp = config.json_format_temperature(temperature)
            
            if _temp in config.json_all_temperatures:
                value = self.__temperatures[_temp]
            else:
                value = _temp
        
        logger.debug('temperature "{}" converted to {}'.format(temperature,value))
        
        return float(value)
    
    
    def should_the_heating_be_on(self, current_temperature):
        """Return True if now the heating should be on, False otherwise"""
        
        logger.debug('checking current should-be status of the heating')

        result = None

        with self.__lock:
            logger.debug('lock acquired to check the should-be status')
            
            if self.__timetable is None:
                logger.debug('empty timetable, cannot check current should-be status')
                raise RuntimeError('the timetable is empty, cannot check current should-be status')
            
            logger.debug('status: {}, current_temperature: {}'.format(self.__status, current_temperature))
            
            if self.__status == config.json_status_on:
                result = True
            elif self.__status == config.json_status_off:
                result = False
            elif self.__status in config.json_all_temperatures:
                logger.debug('target_temperature: {}'.format(self.__temperatures[self.__status]))
                result = (self.degrees(current_temperature) < self.degrees(self.__temperatures[self.__status]))
            elif self.__status == config.json_status_auto:
                now = datetime.now()

                day = config.json_days_name_map[now.strftime('%w')]
                hour = config.json_format_hour(now.hour)
                quarter = int(now.minute // 15)
                
                target_temperature = self.__timetable[day][hour][quarter]

                logger.debug('day: {}, hour: {}, quarter: {}, target_temperature: {}'.format(day, hour, quarter, target_temperature))
                result = (self.degrees(current_temperature) < self.degrees(target_temperature))
        
        logger.debug('the heating should be on: {}'.format(result))

        return result
