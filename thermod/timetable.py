# this module is the timetable

import json
import logging
from threading import RLock
from datetime import datetime
from thermod import config

# TODO mancano tutte le eccezioni
# TODO c'è da scrivere come aggiornare a runtime e quindi salvare su json le modifiche
# TODO write unit-test

__updated__ = '2015-09-16'

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
        logger.debug('(re)loading timetable from json file "{}"'.format(self.filepath))
        
        with self.__lock:
            logger.debug('lock acquired to (re)load timetable')
            
            # loading json file
            logger.debug('opening json file')
            with open(self.filepath, 'r') as file:
                settings = json.load(file)
                status = settings[config.json_status]
                temperatures = settings[config.json_temperatures]
                timetable = settings[config.json_timetable]
                logger.debug('json file loaded')
            
            # checking json content
            logger.debug('checking json content')
            
            # TODO questo controllo deve essere fatto meglio: si deve scorrere
            # tutto il timetable per trovare ogni ora di ogni giorno, se poi
            # ci sono delle configurazioni in più pace, tanto non danno noia,
            # non verranno usate dal programma
            if status not in config.json_all_statuses:
                logger.debug('invalid status ({}) in json file'.format(status))
                raise ValueError('invalid status in timetable file, the status must be one of the following values: ' + ', '.join(config.json_all_statuses))
            
            if set(temperatures.keys()) != set(config.json_all_temperatures):
                logger.debug('missing or invalid temperature name in json file')
                raise ValueError('missing or invalid temperature name in timetable file, the file must contain exactly the following names: ' + ', '.join(config.json_all_temperatures))
            
            if set(timetable.keys()) != set(config.json_days_name_map.values()):
                logger.debug('missing or invalid day name in json file')
                raise ValueError('missing or invalid day name in timetable file, the file must contain every day with these names: ' + ', '.join(config.json_days_name_map.values()))
            
            for (day, hours) in timetable.items():
                for (hour, quarters) in hours.items():
                    if set(map(config.is_valid_temperature, quarters)) != set([True]):
                        logger.debug('invalid temperature in json file for day "{}" and hour "{}"'.format(day,hour))
                        raise ValueError('invalid temperature in timetable file for day "{}" and hour "{}", '
                                         'the temperature must be a number or one of the following values: '.format(day,hour) + ', '.join(config.json_all_temperatures))
            
            logger.debug('json content valid, storing internal variables')
            
            self.__status = status
            self.__temperatures = temperatures
            self.__timetable = timetable
        
        logger.debug('timetable (re)loaded')
    
    
    def save(self, filepath=None):
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
