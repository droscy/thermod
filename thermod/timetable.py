# this module is the timetable

import json
from thermod import config
from threading import RLock
from datetime import datetime

# TODO mancano tutte le eccezioni
# TODO c'è da scrivere come aggiornare a runtime e quindi salvare su json le modifiche
# TODO write unit-test

__updated__ = '2015-09-13'


class TimeTable():

    def __init__(self, filepath):
        """Init the timetable from a json file.

        The filepath must be a full path to the json file that
        contains all the informations to setup the timetable.
        """

        self.__status = None
        self.__timetable = None
        self.__temperatures = None

        self.__lock = RLock()

        self.filepath = filepath
        self.reload()
            

    def reload(self):
        with self.__lock:
            # loading json file
            with open(self.filepath, 'r') as file:
                settings = json.load(file)
                self.__status = settings[config.json_status]
                self.__temperatures = settings[config.json_temperatures]
                self.__timetable = settings[config.json_timetable]

            # checking json content
            if self.__status not in config.json_all_statuses:
                raise ValueError('the status in the timetable is not valid, it must be one of the following values: ' + ', '.join(config.json_all_statuses))

            if set(self.__temperatures.keys()) != set(config.json_all_temperatures):
                raise ValueError('missing or invalid temperature name in timetable, it must contain exactly the following names: ' + ', '.join(config.json_all_temperatures))

            if set(self.__timetable.keys()) != set(config.json_days_name_map.values()):
                raise ValueError('missing or invalid day name in timetable, it must contain every day with these names: ' + ', '.join(config.json_days_name_map.values()))

            for (day, hours) in self.__timetable.items():
                for (hour, quarters) in hours.items():
                    if set(map(config.is_valid_temperature, quarters)) != set([True]):
                        raise ValueError('invalid temperature in timetable for day "{}" and hour "{}", '
                                         'it must be a number or one of the following values : '.format(day,hour) + ', '.join(config.json_all_temperatures))

    def save(self, filepath=None):
        with self.__lock:
            if self.__timetable is None:
                raise RuntimeError('the timetable is empty, cannot be saved')

            with open(filepath or self.__json_file_path, 'w') as file:
                settings = {config.json_status: self.__status,
                            config.json_temperatures: self.__temperatures,
                            config.json_timetable: self.__timetable}

                json.dump(settings, file, indent=2, sort_keys=True)

    def update(self, day, hour, quarter, temperature):
        with self.__lock:
            if self.__timetable is None:
                raise RuntimeError('the timetable is empty, cannot be updated')

            # get day name
            if day in config.json_days_name_map.keys():
                _day = config.json_days_name_map[day]
            elif day in config.json_days_name_map.values():
                _day = day
            else:
                raise ValueError('the provided day name or number ({}) is not valid'.format(day))

            # check hour validity
            _hour = config.json_format_hour(hour)

            # check validity of quarter of an hour
            if int(float(quarter)) in range(4):
                _quarter = int(float(quarter))
            else:
                raise ValueError('the provided quarter is not valid ({}), it must be in range 0-3'.format(quarter))

            # update timetable
            self.__timetable[_day][_hour][_quarter] = config.json_format_temperature(temperature)

    def degrees(self, temperature):
        """Convert the name of a temperature in its corresponding number value.

        If temperature is already a number, it is returned.
        """

        value = None

        with self.__lock:
            _temp = config.json_format_temperature(temperature)
            
            if _temp in config.json_all_temperatures:
                value = self.__temperatures[_temp]
            else:
                value = _temp
        
        return float(value)

    def should_be_on(self, current_temperature):
        """Return True if now the heating must be on, False otherwise"""

        result = None

        with self.__lock:
            if self.__timetable is None:
                raise RuntimeError('the timetable is empty, cannot check current to-be status')

            if self.__status == config.json_status_on:
                result = True
            elif self.__status == config.json_status_off:
                result = False
            elif self.__status in config.json_all_temperatures:
                result = (self.degrees(current_temperature) < self.degrees(self.__temperatures[self.__status]))
            elif self.__status == config.json_status_auto:
                now = datetime.now()

                day = config.json_days_name_map[now.strftime('%w')]
                hour = config.json_format_hour(now.hour)
                quarter = int(now.minute // 15)
                
                target_temperature = self.__timetable[day][hour][quarter]
                
                print((day,hour,quarter,target_temperature)) # TODO mettere un logger nel package
                print((self.degrees(current_temperature),self.degrees(target_temperature)))
                
                result = (self.degrees(current_temperature) < self.degrees(target_temperature))

        return result
