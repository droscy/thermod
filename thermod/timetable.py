"""Manage the timetable of thermod."""

import json
import logging
import jsonschema
from threading import RLock
from datetime import datetime, timedelta
from thermod import config
from thermod.config import JsonValueError

# TODO write unit-test

__docformat__ = 'restructuredtext'
__updated__ = '2015-10-11'

logger = logging.getLogger(__name__)

class TimeTable():
    """Represent the timetable to control the heating."""
    
    def __init__(self, filepath=None):
        """Init the timetable.

        If the `filepath` is not `None`, it must be a full path to a
        JSON file that contains all the informations to setup the
        timetable.
        """
        
        logger.debug('initializing timetable')

        self.__status = None
        self.__temperatures = None
        self.__timetable = None
        self.__differential = 0.5
        
        self.__grace_time = timedelta(seconds=3600)

        self.__lock = RLock()
        self.__is_on = False  # if the heating is on
        self.__last_on_time = datetime(1,1,1)  # last switch on time
        
        self.filepath = filepath
        
        if self.filepath is not None:
            self.reload()
    
    
    def reload(self):
        # TODO bisogna gestire la situazione in cui self.filepath non sia una stringa o che il file non si possa leggere
        """Reload the timetable from JSON file.
        
        The JSON file is the same provided in `TimeTable.__init__()`
        method, thus if a different file is needed, set a new
        `self.filepath` to the full path before calling this method.
        
        If the JSON file is invalid (or `self.filepath` is not a string)
        an exception is raised and the internal settings remain unchanged.
        """
        
        logger.debug('(re)loading timetable')
        
        with self.__lock:
            logger.debug('lock acquired to (re)load timetable')
            
            if self.filepath is None:
                logger.debug('filepath not set, cannot continue')
                raise RuntimeError('no timetable file provided, cannot (re)load data')
            
            # loading json file
            with open(self.filepath, 'r') as file:
                try:
                    logger.debug('loading json file: {}'.format(self.filepath))
                    settings = json.load(file)
                except ValueError:
                    logger.debug('not a json file, cannot continue')
                    raise JsonValueError('the timetable file is not in json format')
                
                logger.debug('validating json file')
                jsonschema.validate(settings, config.json_schema)
                
                logger.debug('json file loaded and validated')
            
            self.__status = settings[config.json_status]
            self.__temperatures = settings[config.json_temperatures]
            self.__timetable = settings[config.json_timetable]
            
            if config.json_differential in settings:
                self.__differential = settings[config.json_differential]
            
            if config.json_grace_time in settings:
                self.__grace_time = timedelta(seconds=settings[config.json_grace_time])
            
            # converting hours to integer in order to avoid problems with leading zero
            #self.__timetable = {day:{int(h):q for h,q in hours.items()} for day,hours in settings[config.json_timetable].items()}
            
            logger.debug('current status: {}'.format(self.__status))
            logger.debug('temperatures: t0={t0}, tmin={tmin}, tmax={tmax}'.format(**self.__temperatures))
            logger.debug('differential: {} degrees'.format(self.__differential))
            logger.debug('grace time: {}'.format(self.__grace_time))
        
        logger.debug('timetable (re)loaded')
    
    
    def save(self, filepath=None):
        """Save the current timetable to JSON file.
        
        Save the current configuration of the timetable to a JSON file
        pointed by `filepath` (full path to file). I `filepath` is
        `None`, settings are saved to `self.filepath`.
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
                            config.json_differential: self.__differential,
                            config.json_grace_time: int(self.__grace_time.total_seconds()),
                            config.json_temperatures: self.__temperatures,
                            config.json_timetable: self.__timetable}
                
                json.dump(settings, file, indent=2, sort_keys=True)
        
        logger.debug('timetable saved')
    
    
    @property
    def status(self):
        """Return the current status."""
        with self.__lock:
            logger.debug('lock acquired to get current status')
            return self.__status
    
    
    @status.setter
    def status(self,status):
        """Set a new status."""
        with self.__lock:
            logger.debug('lock acquired to set a new status')
            
            if status not in config.json_all_statuses:
                logger.debug('invalid new status: {}'.format(status))
                raise JsonValueError(
                    'the new status ({}) is invalid, it must be one of [{}]. '
                    'Falling back to the previews one: {}'.format(
                        status,
                        ', '.join(config.json_all_statuses),
                        self.__status))
            
            self.__status = status
            logger.debug('new status set: {}'.format(status))
    
    
    @property
    def differential(self):
        """Return the current differential value."""
        with self.__lock:
            logger.debug('lock acquired to get current differntial value')
            return self.__differential
    
    
    @differential.setter
    def differential(self,value):
        """Set a new differential value."""
        with self.__lock:
            logger.debug('lock acquired to set a new differential value')
            
            try:
                nvalue = config.json_format_main_temperature(value)
                
                if nvalue < 0 or nvalue > 1:
                    raise JsonValueError()
            
            # i catch and raise again the same exception to change the message
            except JsonValueError:
                logger.debug('invalid new differential value: {}'.format(value))
                raise JsonValueError(
                    'the new differential value ({}) is invalid, '
                    'it must be a number in range [0;1]'.format(value))
            
            self.__differential = nvalue
            logger.debug('new differential value set: {}'.format(nvalue))
    
    
    @property
    def grace_time(self):
        """Return the current grace time in *seconds*."""
        with self.__lock:
            logger.debug('lock acquired to get current grace time')
            return int(self.__grace_time.total_seconds())
    
    
    @grace_time.setter
    def grace_time(self,seconds):
        """Set a new grace time in *seconds*."""
        with self.__lock:
            logger.debug('lock acquired to set a new grace time')
            
            try:
                nvalue = int(seconds)
                
                if nvalue < 0:
                    raise ValueError()
            
            except:
                logger.debug('invalid new grace time: {}'.format(seconds))
                raise JsonValueError(
                    'the new grace time ({}) is invalid, '
                    'it must be a number expressed in seconds'.format(seconds))
            
            self.__grace_time = timedelta(seconds=nvalue)
            logger.debug('new grace time set: {} sec = {}'.format(nvalue, self.__grace_time))
    
    
    @property
    def t0(self):
        """Return the current value for ``t0`` temperature."""
        with self.__lock:
            logger.debug('lock acquired to get current t0 temperature')
            return self.__temperatures[config.json_t0_str]
    
    
    @t0.setter
    def t0(self,value):
        """Set a new value for ``t0`` temperature."""
        with self.__lock:
            logger.debug('lock acquired to set a new t0 value')
            
            try:
                nvalue = config.json_format_main_temperature(value)
            # i catch and raise again the same exception to change the message
            except JsonValueError:
                logger.debug('invalid new value for t0 temperature: {}'.format(value))
                raise JsonValueError(
                    'the new value ({}) for t0 temperature '
                    'is invalid, it must be a number'.format(value))
            
            self.__temperatures[config.json_t0_str] = nvalue
            logger.debug('new t0 temperature set: {}'.format(value))
    
    
    @property
    def tmin(self):
        """Return the current value for ``tmin`` temperature."""
        with self.__lock:
            logger.debug('lock acquired to get current tmin temperature')
            return self.__temperatures[config.json_tmin_str]
    
    
    @tmin.setter
    def tmin(self,value):
        """Set a new value for ``tmin`` temperature."""
        with self.__lock:
            logger.debug('lock acquired to set a new tmin value')
            
            try:
                nvalue = config.json_format_main_temperature(value)
            # i catch and raise again the same exception to change the message
            except JsonValueError:
                logger.debug('invalid new value for tmin temperature: {}'.format(value))
                raise JsonValueError(
                    'the new value ({}) for tmin temperature '
                    'is invalid, it must be a number'.format(value))
            
            self.__temperatures[config.json_tmin_str] = nvalue
            logger.debug('new tmin temperature set: {}'.format(value))
    
    
    @property
    def tmax(self):
        """Return the current value for ``tmax`` temperature."""
        with self.__lock:
            logger.debug('lock acquired to get current tmax temperature')
            return self.__temperatures[config.json_tmax_str]
    
    
    @tmax.setter
    def tmax(self,value):
        """Set a new value for ``tmax`` temperature."""
        with self.__lock:
            logger.debug('lock acquired to set a new tmax value')
            
            try:
                nvalue = config.json_format_main_temperature(value)
            # i catch and raise again the same exception to change the message
            except JsonValueError:
                logger.debug('invalid new value for tmax temperature: {}'.format(value))
                raise JsonValueError(
                    'the new value ({}) for tmax temperature '
                    'is invalid, it must be a number'.format(value))
            
            self.__temperatures[config.json_tmax_str] = nvalue
            logger.debug('new tmax temperature set: {}'.format(nvalue))
    
    
    def update(self, day, hour, quarter, temperature):
        # TODO scrivere documentazione
        logger.debug('updating timetable: day "{}", hour "{}", quarter "{}", '
                     'temperature "{}"'.format(day, hour, quarter, temperature))
        
        with self.__lock:
            logger.debug('lock acquired to update timetable')
            
            if self.__timetable is None:
                logger.debug('empty timetable, cannot be updated')
                raise RuntimeError('the timetable is empty, cannot be updated')
            
            # get day name
            logger.debug('retriving day name')
            if day in config.json_days_name_map.keys():
                _day = config.json_days_name_map[day]
            elif day in set(config.json_days_name_map.values()):
                _day = day
            else:
                logger.debug('invalid day name or number: {}'.format(day))
                raise JsonValueError('the provided day name or number ({}) '
                                     'is not valid'.format(day))
            
            # check hour validity
            logger.debug('checking and formatting hour')
            _hour = config.json_format_hour(hour)
            
            # check validity of quarter of an hour
            logger.debug('checking validity of quarter')
            if int(float(quarter)) in range(4):
                _quarter = int(float(quarter))
            else:
                logger.debug('invalid quarter: {}'.format(quarter))
                raise JsonValueError('the provided quarter is not valid ({}), '
                                     'it must be in range 0-3'.format(quarter))
            
            # format temperature and check validity
            _temp = config.json_format_temperature(temperature)
            
            # update timetable
            self.__timetable[_day][_hour][_quarter] = _temp
        
        logger.debug('timetable updated: day "{}", hour "{}", quarter "{}", '
                     'temperature "{}"'.format(_day, _hour, _quarter, _temp))
    
    
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
        """Return `True` if now the heating *should be* ON, `False` otherwise.
        
        This method doesn't update any of the internal variables,
        i.e. if the heating should be on, `self.__is_on` and
        `self.__last_on_time` remain the same until `self.seton()`
        is executed.
        """
        
        logger.debug('checking current should-be status of the heating')

        shoud_be_on = None
        
        with self.__lock:
            logger.debug('lock acquired to check the should-be status')
            
            if self.__timetable is None:
                logger.debug('empty timetable, cannot check current should-be status')
                raise RuntimeError('the timetable is empty, cannot check current should-be status')
            
            current = self.degrees(current_temperature)
            diff = self.degrees(self.__differential)
            logger.debug('status: {}, current_temperature: {}, differential: {}'
                         .format(self.__status, current, diff))
            
            if self.__status == config.json_status_on:  # always on
                shoud_be_on = True
            
            elif self.__status == config.json_status_off:  # always off
                shoud_be_on = False
            
            else:  # checking against current temperature and timetable
                now = datetime.now()
                
                if self.__status in config.json_all_temperatures:
                    # target temperature is set manually
                    target = self.degrees(self.__temperatures[self.__status])
                    logger.debug('target_temperature: {}'.format(target))
                
                elif self.__status == config.json_status_auto:
                    # target temperature is retrived from timetable
                    day = config.json_days_name_map[now.strftime('%w')]
                    hour = config.json_format_hour(now.hour)
                    quarter = int(now.minute // 15)
                    
                    target = self.degrees(self.__timetable[day][hour][quarter])
                    
                    logger.debug('day: {}, hour: {}, quarter: {}, '
                                 'target_temperature: {}'
                                 .format(day, hour, quarter, target))
                
                laston = self.__is_on
                lotime = self.__last_on_time
                grace = self.__grace_time
                
                shoud_be_on = (
                    (current < (target - diff))
                    or ((current <= target) and ((now - lotime) > grace))
                    or ((current < (target + diff)) and laston))
        
        logger.debug('the heating should be: {}'
                     .format((shoud_be_on and 'ON')
                             or (not shoud_be_on and 'OFF')))
        
        return shoud_be_on
    
    
    def seton(self):
        """The heating is ON, set internal variable to reflect this status.
        
        In other part of the program someone switched on the heating and
        the timetable must be informed of this change, thus call this
        method to set `self.__is_on` and `self.__last_on_time`.
        """
        with self.__lock:
            logger.debug('lock acquired to set on')
            self.__is_on = True
            self.__last_on_time = datetime.now()
            logger.debug('is-on set to "{}" and last-on-time set to "{}"'
                         .format(self.__is_on, self.__last_on_time))
    
    
    def setoff(self):
        """The heating is OFF, set internal variable to reflect this status."""
        with self.__lock:
            logger.debug('lock acquired to set off')
            self.__is_on = False
            logger.debug('is-on set to "{}"'.format(self.__is_on))
