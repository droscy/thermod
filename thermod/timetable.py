"""Manage the timetable of thermod."""

import json
import logging
import jsonschema
from threading import RLock
from datetime import datetime, timedelta

from . import config
from .config import JsonValueError

# TODO passare a Doxygen dato che lo conosco meglio!
# TODO controllare se serve copy.deepcopy() nella gestione degli array letti da json

__docformat__ = 'restructuredtext'
__updated__ = '2015-11-26'

logger = logging.getLogger(__name__)

class TimeTable():
    """Represent the timetable to control the heating."""
    
    def __init__(self, filepath=None):
        """Init the timetable.

        If `filepath` is not `None`, it must be a full path to a
        JSON file that contains all the informations to setup the
        timetable.
        """
        
        logger.debug('initializing timetable')

        self._status = None
        self._temperatures = {}
        self._timetable = {}
        self._differential = 0.5
        
        self._grace_time = timedelta(seconds=3600)

        self._lock = RLock()
        self._is_on = False  # if the heating is on
        self._last_on_time = datetime(1,1,1)  # last switch on time
        
        self._has_been_validated = False
        """Used to speedup validation.
        
        Whenever a full validation has already been performed and no
        change has occurred, the object is still valid, no need to
        validate again.
        
        If it isn't `True` it means only that a full validation hasn't
        been performed yet, but the object can be valid.
        """
        
        self.filepath = filepath
        
        if self.filepath is not None:
            self.reload()
    
    
    def __eq__(self, other):
        """Check if two `TimeTable`'s have the same temperatures and timetable.
        
        The check is performed only on main temperatures, timetable,
        differential value and grace time because the other attributes
        (status, is_on, last_on_time, is_valid and filepath) are relative
        to the current usage of the `TimeTable` object.
        """
        
        result = None
        
        try:
            if (isinstance(other, self.__class__)
                    and (self._temperatures == other._temperatures)
                    and (self._timetable == other._timetable)
                    and (self._differential == other._differential)
                    and (self._grace_time == other._grace_time)):
                result = True
            else:
                result = False
        except AttributeError:
            result = False
        
        return result
    
    
    def __getstate__(self):
        """Validate the internal settings and return them as a dictonary.
        
        The returned dictonary can be used to save the data in a JSON file.
        The validation is performed even if `TimeTable._has_been_validated`
        is True.
        """
        
        logger.debug('validating timetable and returning internal state')
        
        with self._lock:
            logger.debug('lock acquired to validate timetable')
            
            settings = {config.json_status: self._status,
                        config.json_differential: self._differential,
                        config.json_grace_time: int(self._grace_time.total_seconds()),
                        config.json_temperatures: self._temperatures,
                        config.json_timetable: self._timetable}
            
            jsonschema.validate(settings, config.json_schema)
            logger.debug('the timetable is valid')
        
        logger.debug('returning internal state')
        return settings
    
    
    def __setstate__(self, state):
        """Set the internal state.
        
        The `state` is first validated, if it is valid the internal
        variable will be set, otherwise a `jsonschema.ValidationError`
        exception is raised.
        """
        
        # Init this object only if the _lock attribute is missing, that means
        # that this method has been called during a copy of a TimeTable object.
        if not hasattr(self, '_lock'):
            logger.debug('setting state to an empty timetable')
            self.__init__(None)
        
        logger.debug('storing internal state')
        
        with self._lock:
            logger.debug('validating received json data')
            jsonschema.validate(state, config.json_schema)
            
            logger.debug('data validated: storing variables')
            self._status = state[config.json_status]
            self._temperatures = state[config.json_temperatures]
            self._timetable = state[config.json_timetable]
            
            if config.json_differential in state:
                self._differential = state[config.json_differential]
            
            if config.json_grace_time in state:
                self._grace_time = timedelta(seconds=state[config.json_grace_time])
            
            logger.debug('current status: {}'.format(self._status))
            logger.debug('temperatures: t0={t0}, tmin={tmin}, tmax={tmax}'.format(**self._temperatures))
            logger.debug('differential: {} degrees'.format(self._differential))
            logger.debug('grace time: {}'.format(self._grace_time))
        
            self._validate()
        
        logger.debug('internal state set')
    
    
    def _validate(self):
        """Validate the internal settings.
        
        A full validation is performed only if `TimeTable._has_been_validated`
        is not `True`, otherwise silently exits without errors.
        """
        
        with self._lock:
            if not self._has_been_validated:
                self.__getstate__()
                
                # if no exception is raised
                self._has_been_validated = True
    
    
    @property
    def lock(self):
        """Return the internal reentrant lock to be acquired externally."""
        logger.debug('returning internal lock to be acquired externally')
        return self._lock
    
    
    def reload(self):
        """Reload the timetable from JSON file.
        
        The JSON file is the same provided in `TimeTable.__init__()`
        method, thus if a different file is needed, set a new
        `TimeTable.filepath` to the full path before calling this method.
        
        If the JSON file is invalid (or `self.filepath` is not a string)
        an exception is raised and the internal settings remain unchanged.
        The exceptions can be:
        
        - `RuntimeError` if no file provided
        - `OSError` if the file cannot be found/read or other OS related errors
        - `ValueError` if the file is not in JSON format or
          the JSON content has syntax errors
        - `jsonschema.ValidationError` if the JSON content is not valid
        """
        
        logger.debug('(re)loading timetable')
        
        with self._lock:
            logger.debug('lock acquired to (re)load timetable')
            
            if not self.filepath:  # empty string or None
                logger.debug('filepath not set, cannot continue')
                raise RuntimeError('no timetable file provided, cannot (re)load data')
            
            # loading json file
            with open(self.filepath, 'r') as file:
                logger.debug('loading json file: {}'.format(self.filepath))
                settings = json.load(file)
                logger.debug('json file loaded')
            
            self.__setstate__(settings)
        
        logger.debug('timetable (re)loaded')
    
    
    def save(self, filepath=None):
        """Save the current timetable to JSON file.
        
        Save the current configuration of the timetable to a JSON file
        pointed by `filepath` (full path to file). If `filepath` is
        `None`, settings are saved to `self.filepath`.
        
        Raise the following exceptions on error:
        - `jsonschema.ValidationError` if the current timetable is not valid
        - `OSError` if the file cannot be written or other OS related errors
        """
        
        logger.debug('saving timetable to file')
        
        with self._lock:
            logger.debug('lock acquired to save timetable')
            
            if not (filepath or self.filepath):  # empty strings or None
                logger.debug('filepath not set, cannot save timetable')
                raise RuntimeError('no timetable file provided, cannot save data')
            
            # validate and retrive settings
            settings = self.__getstate__()
            
            with open(filepath or self.filepath, 'w') as file:
                logger.debug('saving timetable to json file {}'.format(file.name))
                json.dump(settings, file, indent=2, sort_keys=True)
        
        logger.debug('timetable saved')
    
    
    @property
    def status(self):
        """Return the current status."""
        with self._lock:
            logger.debug('lock acquired to get current status')
            return self._status
    
    
    @status.setter
    def status(self,status):
        """Set a new status."""
        with self._lock:
            logger.debug('lock acquired to set a new status')
            
            if status not in config.json_all_statuses:
                logger.debug('invalid new status: {}'.format(status))
                raise JsonValueError(
                    'the new status ({}) is invalid, it must be one of [{}]. '
                    'Falling back to the previews one: {}'.format(
                        status,
                        ', '.join(config.json_all_statuses),
                        self._status))
            
            self._status = status
            self._has_been_validated = False
            logger.debug('new status set: {}'.format(status))
    
    
    @property
    def differential(self):
        """Return the current differential value."""
        with self._lock:
            logger.debug('lock acquired to get current differntial value')
            return self._differential
    
    
    @differential.setter
    def differential(self,value):
        """Set a new differential value."""
        with self._lock:
            logger.debug('lock acquired to set a new differential value')
            
            try:
                nvalue = config.json_format_main_temperature(value)
                
                if nvalue < 0 or nvalue > 1:
                    raise ValueError()
            
            # i catch and raise again the same exception to change the message
            except:
                logger.debug('invalid new differential value: {}'.format(value))
                raise JsonValueError(
                    'the new differential value ({}) is invalid, '
                    'it must be a number in range [0;1]'.format(value))
            
            self._differential = nvalue
            self._has_been_validated = False
            logger.debug('new differential value set: {}'.format(nvalue))
    
    
    @property
    def grace_time(self):
        """Return the current grace time in *seconds*."""
        with self._lock:
            logger.debug('lock acquired to get current grace time')
            return int(self._grace_time.total_seconds())
    
    
    @grace_time.setter
    def grace_time(self,seconds):
        """Set a new grace time in *seconds*."""
        with self._lock:
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
            
            self._grace_time = timedelta(seconds=nvalue)
            self._has_been_validated = False
            logger.debug('new grace time set: {} sec = {}'.format(nvalue, self._grace_time))
    
    
    @property
    def t0(self):
        """Return the current value for ``t0`` temperature."""
        with self._lock:
            logger.debug('lock acquired to get current t0 temperature')
            return self._temperatures[config.json_t0_str]
    
    
    @t0.setter
    def t0(self,value):
        """Set a new value for ``t0`` temperature."""
        with self._lock:
            logger.debug('lock acquired to set a new t0 value')
            
            try:
                nvalue = config.json_format_main_temperature(value)
            
            # i catch and raise again the same exception to change the message
            except:
                logger.debug('invalid new value for t0 temperature: {}'.format(value))
                raise JsonValueError(
                    'the new value ({}) for t0 temperature '
                    'is invalid, it must be a number'.format(value))
            
            self._temperatures[config.json_t0_str] = nvalue
            self._has_been_validated = False
            logger.debug('new t0 temperature set: {}'.format(nvalue))
    
    
    @property
    def tmin(self):
        """Return the current value for ``tmin`` temperature."""
        with self._lock:
            logger.debug('lock acquired to get current tmin temperature')
            return self._temperatures[config.json_tmin_str]
    
    
    @tmin.setter
    def tmin(self,value):
        """Set a new value for ``tmin`` temperature."""
        with self._lock:
            logger.debug('lock acquired to set a new tmin value')
            
            try:
                nvalue = config.json_format_main_temperature(value)
            
            # i catch and raise again the same exception to change the message
            except:
                logger.debug('invalid new value for tmin temperature: {}'.format(value))
                raise JsonValueError(
                    'the new value ({}) for tmin temperature '
                    'is invalid, it must be a number'.format(value))
            
            self._temperatures[config.json_tmin_str] = nvalue
            self._has_been_validated = False
            logger.debug('new tmin temperature set: {}'.format(nvalue))
    
    
    @property
    def tmax(self):
        """Return the current value for ``tmax`` temperature."""
        with self._lock:
            logger.debug('lock acquired to get current tmax temperature')
            return self._temperatures[config.json_tmax_str]
    
    
    @tmax.setter
    def tmax(self,value):
        """Set a new value for ``tmax`` temperature."""
        with self._lock:
            logger.debug('lock acquired to set a new tmax value')
            
            try:
                nvalue = config.json_format_main_temperature(value)
            
            # i catch and raise again the same exception to change the message
            except:
                logger.debug('invalid new value for tmax temperature: {}'.format(value))
                raise JsonValueError(
                    'the new value ({}) for tmax temperature '
                    'is invalid, it must be a number'.format(value))
            
            self._temperatures[config.json_tmax_str] = nvalue
            self._has_been_validated = False
            logger.debug('new tmax temperature set: {}'.format(nvalue))
    
    
    def update(self, day, hour, quarter, temperature):
        # TODO scrivere documentazione
        logger.debug('updating timetable: day "{}", hour "{}", quarter "{}", '
                     'temperature "{}"'.format(day, hour, quarter, temperature))
        
        with self._lock:
            logger.debug('lock acquired to update a temperature in timetable')
            
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
            try:
                if int(float(quarter)) in range(4):
                    _quarter = int(float(quarter))
                else:
                    raise Exception()
            except:
                logger.debug('invalid quarter: {}'.format(quarter))
                raise JsonValueError('the provided quarter is not valid ({}), '
                                     'it must be in range 0-3'.format(quarter))
            
            # format temperature and check validity
            _temp = config.json_format_temperature(temperature)
            
            # if the day is missing, add it to the timetable
            if _day not in self._timetable.keys():
                self._timetable[_day] = {}
            
            # if the hour is missing, add it to the timetable
            if _hour not in self._timetable[_day].keys():
                self._timetable[_day][_hour] = [None, None, None, None]
            
            # update timetable
            self._timetable[_day][_hour][_quarter] = _temp
            self._has_been_validated = False
        
        logger.debug('timetable updated: day "{}", hour "{}", quarter "{}", '
                     'temperature "{}"'.format(_day, _hour, _quarter, _temp))
    
    
    def degrees(self, temperature):
        """Convert the name of a temperature in its corresponding number value.
        
        If temperature is already a number, the number itself is returned.
        If the main temperatures aren't set yet a `RuntimeError` is raised.
        """
        
        logger.debug('converting temperature name to degrees')
        
        value = None
        
        with self._lock:
            logger.debug('lock acquired to convert temperature name')
            
            if not self._temperatures:
                logger.debug('no main temperature provided')
                raise RuntimeError('no main temperature provided, '
                                   'cannot convert name to degrees')
            
            temp = config.json_format_temperature(temperature)
            
            if temp in config.json_all_temperatures:
                value = self._temperatures[temp]
            else:
                value = temp
        
        logger.debug('temperature "{}" converted to {}'.format(temperature,value))
        
        return float(value)
    
    
    def should_the_heating_be_on(self, current_temperature):
        """Return `True` if now the heating *should be* ON, `False` otherwise.
        
        This method doesn't update any of the internal variables,
        i.e. if the heating should be on, `self._is_on` and
        `self._last_on_time` remain the same until `self.seton()`
        is executed.
        """
        
        logger.debug('checking current should-be status of the heating')
        
        shoud_be_on = None
        self._validate()
        
        with self._lock:
            logger.debug('lock acquired to check the should-be status')
            
            current = self.degrees(current_temperature)
            diff = self.degrees(self._differential)
            logger.debug('status: {}, current_temperature: {}, differential: {}'
                         .format(self._status, current, diff))
            
            if self._status == config.json_status_on:  # always on
                shoud_be_on = True
            
            elif self._status == config.json_status_off:  # always off
                shoud_be_on = False
            
            else:  # checking against current temperature and timetable
                now = datetime.now()
                
                if self._status in config.json_all_temperatures:
                    # target temperature is set manually
                    target = self.degrees(self._temperatures[self._status])
                    logger.debug('target_temperature: {}'.format(target))
                
                elif self._status == config.json_status_auto:
                    # target temperature is retrived from timetable
                    day = config.json_days_name_map[now.strftime('%w')]
                    hour = config.json_format_hour(now.hour)
                    quarter = int(now.minute // 15)
                    
                    target = self.degrees(self._timetable[day][hour][quarter])
                    logger.debug('day: {}, hour: {}, quarter: {}, '
                                 'target_temperature: {}'
                                 .format(day, hour, quarter, target))
                
                ison = self._is_on
                laston = self._last_on_time
                grace = self._grace_time
                
                shoud_be_on = (
                    (current <= (target - diff))
                    or ((current < target) and ((now - laston) > grace))
                    or ((current < (target + diff)) and ison))
        
        logger.debug('the heating should be: {}'
                     .format((shoud_be_on and 'ON')
                             or (not shoud_be_on and 'OFF')))
        
        return shoud_be_on
    
    
    def seton(self):
        """The heating is ON, set internal variable to reflect this status.
        
        In other part of the program someone switched on the heating and
        the timetable must be informed of this change, thus call this
        method to set `self._is_on` and `self._last_on_time` attributes.
        """
        
        with self._lock:
            logger.debug('lock acquired to set on')
            self._is_on = True
            self._last_on_time = datetime.now()
            logger.debug('is-on set to "{}" and last-on-time set to "{}"'
                         .format(self._is_on, self._last_on_time))
    
    
    def setoff(self):
        """The heating is OFF, set internal variable to reflect this status."""
        
        with self._lock:
            logger.debug('lock acquired to set off')
            self._is_on = False
            logger.debug('is-on set to "{}"'.format(self._is_on))
