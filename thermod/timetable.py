# -*- coding: utf-8 -*-
"""Manage the timetable of Thermod.

Copyright (C) 2016 Simone Rossetto <simros85@gmail.com>

This file is part of Thermod.

Thermod is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Thermod is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Thermod.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import json
import logging
import jsonschema
import os.path
import time
import math
from copy import copy, deepcopy
from threading import Condition
from datetime import datetime

# backward compatibility for Python 3.4 (TODO check for better handling)
if sys.version[0:3] >= '3.5':
    from json.decoder import JSONDecodeError
else:
    JSONDecodeError = ValueError

from . import config
from .config import JsonValueError
from .heating import BaseHeating
from .memento import transactional
from .thermometer import BaseThermometer, FakeThermometer

# TODO passare a Doxygen dato che lo conosco meglio (doxypy oppure doxypypy)
# TODO forse JsonValueError può essere tolto oppure il suo uso limitato, da pensarci

__date__ = '2015-09-09'
__updated__ = '2017-01-29'
__version__ = '1.3'

logger = logging.getLogger(__name__)



class ShouldBeOn(int):
    """Behaves as a boolean with additional attribute for heating status."""
    
    def __new__(cls, should_be_on, *args, **kwargs):
        return int.__new__(cls, bool(should_be_on))
    
    def __init__(self, should_be_on, status=None, curr_temp=None, target_temp=None):
        self.status = status
        self.current_temperature = (curr_temp or float('NaN'))
        self.target_temperature = (target_temp or float('NaN'))
    
    def __repr__(self, *args, **kwargs):
        return '{module}.{cls}({should!r}, {status!r}, {curr!r}, {target!r})'.format(
                    module=self.__module__,
                    cls=self.__class__.__name__,
                    should=bool(self),
                    status=self.status,
                    curr=self.current_temperature,
                    target=self.target_temperature)
    
    def __str__(self, *args, **kwargs):
        return str(bool(self))
    
    @property
    def should_be_on(self):
        return bool(self)



class TimeTable(object):
    """Represent the timetable to control the heating."""
    
    def __init__(self, filepath=None, heating=None, thermometer=None):
        """Init the timetable.
        
        The timetable can be initialized empty, if every paramether is `None`,
        or with full information to control the real heating providing the
        path to the JSON timetable file.

        @param filepath full path to a JSON file that contains all the
            informations to setup the timetable
        
        @param heating must be a subclass of thermod.heating.BaseHeating,
            if `None` a thermod.heating.BaseHeating is used to provide basic
            functionality
        
        @param thermometer must be a subclass of
            thermod.thermometer.BaseThermometer, if `None` a
            thermod.thermometer.FakeThermometer is used to provide basic
            functionality (its `temperature` property always returns 20 degrees)
        
        @see TimeTable.reload() for possible exceptions
        """
        
        logger.debug('initializing {}'.format(self.__class__.__name__))

        self._status = None
        self._temperatures = {}
        self._timetable = {}
        
        self._differential = 0.5
        self._grace_time = float('+Inf')  # disabled by default

        self._lock = Condition()
        """Provide single-thread access to methods of this class."""
        
        if isinstance(heating, BaseHeating):
            self._heating = heating
            """Interface to the real heating."""
        elif not heating:
            # fake heating with basic functionality
            self._heating = BaseHeating()
        else:
            logger.debug('the heating must be a subclass of BaseHeating')
            raise TypeError('the heating must be a subclass of BaseHeating')
        
        if isinstance(thermometer, BaseThermometer):
            self._thermometer = thermometer
            """Interface to the real thermometer."""
        elif not thermometer:
            # fake thermometer with basic functionality
            self._thermometer = FakeThermometer()
        else:
            logger.debug('the thermometer must be a subclass of BaseThermometer')
            raise TypeError('the thermometer must be a subclass of BaseThermometer')
        
        self._has_been_validated = False
        """Used to speedup validation.
        
        Whenever a full validation has already been performed and no
        changes have occurred, the object is still valid, no need to
        validate again.
        
        If it isn't `True` it means only that a full validation hasn't
        been performed yet, but the object can be valid.
        """
        
        self._last_update_timestamp = 0
        """Timestamp of settings last update.
        
        Equal to JSON file mtime if settings loaded from file or equal
        to current timestamp of last settings change.
        """
        
        self._last_tgt_temp_reached_timestamp = config.TIMESTAMP_MAX_VALUE
        """Timestamp of target temperature last reaching.
        
        Whenever the target temperature is reached, this value is updated with
        the current timestamp. When the current temperature falls below the
        target temperature, this value is reset to `config.TIMESTAMP_MAX_VALUE`.
        
        It is used in the `should_the_heating_be_on(room_temperature)`
        method to respect the grace time.
        """
        
        self.filepath = filepath
        """Full path to a JSON timetable configuration file."""
        
        if self.filepath:
            self.reload()
    
    
    def __repr__(self, *args, **kwargs):
        return '{module}.{cls}({filepath!r}, {heating!r}, {thermo!r})'.format(
                    module=self.__module__,
                    cls=self.__class__.__name__,
                    filepath=self.filepath,
                    heating=self._heating,
                    thermo=self._thermometer)
    
    
    def __eq__(self, other):
        """Check if two TimeTable objects have the same settings.
        
        The check is performed only on `status`, main `temperatures`,
        `timetable`, `differential` value and `grace time` because the other
        attributes are relative to the specific usage of the TimeTable object.
        
        @param other the other TimeTable to be compared
        """
        
        try:
            result = (isinstance(other, self.__class__)
                        and (self._status == other._status)
                        and (self._temperatures == other._temperatures)
                        and (self._timetable == other._timetable)
                        and (self._differential == other._differential)
                        and (self._grace_time == other._grace_time))
        
        except AttributeError:
            result = False
        
        return result
    
    
    def __copy__(self):
        """Return a <em>shallow copy</em> of this TimeTable."""
        
        new = self.__class__()
        
        new._status = self._status
        new._temperatures = self._temperatures
        new._timetable = self._timetable
        new._differential = self._differential
        new._grace_time = self._grace_time
    
        new._lock = copy(self._lock)
        
        new._heating = copy(self._heating)
        new._thermometer = copy(self._thermometer)
        
        new._has_been_validated = self._has_been_validated
        new._last_update_timestamp = self._last_update_timestamp
        new._last_tgt_temp_reached_timestamp = self._last_tgt_temp_reached_timestamp
        
        new.filepath = self.filepath
        
        return new
    
    
    def __deepcopy__(self, memodict={}):
        """Return a deep copy of this TimeTable."""
        
        new = self.__class__()
        
        new._status = self._status
        new._temperatures = deepcopy(self._temperatures)
        new._timetable = deepcopy(self._timetable)
        new._differential = self._differential
        new._grace_time = self._grace_time
    
        new._lock = deepcopy(self._lock)
        
        new._heating = deepcopy(self._heating)
        new._thermometer = deepcopy(self._thermometer)
        
        new._has_been_validated = self._has_been_validated
        new._last_update_timestamp = self._last_update_timestamp
        new._last_tgt_temp_reached_timestamp = self._last_tgt_temp_reached_timestamp
        
        new.filepath = self.filepath
        
        return new
    
    
    def __getstate__(self):
        """Validate the internal state and return it as a dictonary.
        
        The returned dictonary is a deep copy of the internal state.
        The validation is performed even if `TimeTable._has_been_validated`
        is True.
        
        @exception jsonschema.ValidationError if the internal state is invalid
        """
        
        logger.debug('validating timetable and returning internal state')
        
        with self._lock:
            logger.debug('lock acquired to validate timetable')
            
            settings = {config.json_status: self._status,
                        config.json_differential: self._differential,
                        config.json_grace_time: self._grace_time,
                        config.json_temperatures: self._temperatures,
                        config.json_timetable: self._timetable}
            
            jsonschema.validate(settings, config.json_schema)
            logger.debug('the timetable is valid')
        
        logger.debug('returning internal state')
        return deepcopy(settings)
    
    
    @transactional(exclude=['_lock', '_heating', '_thermometer'])
    def __setstate__(self, state):
        """Set new internal state.
        
        The new `state` is "deep" copied before saving
        internally to prevent unwanted update to any external array, if it's
        valid it will be set, otherwise a `jsonschema.ValidationError` exception
        is raised and the old state remains unchanged.
        
        @param state the new state to be set
        @exception jsonschema.ValidationError if `state` is invalid
        """
        
        logger.debug('setting new internal state')
        
        # Init this object only if the _lock attribute is missing, that means
        # that this method has been called during a copy of an other
        # TimeTable object.
        if not hasattr(self, '_lock'):
            logger.debug('the timetable is empty')
            self.__init__()
        
        with self._lock:
            logger.debug('lock acquired to set new state')
            
            self._status = state[config.json_status]
            self._temperatures = deepcopy(state[config.json_temperatures])
            self._timetable = deepcopy(state[config.json_timetable])
            
            if config.json_differential in state:
                self._differential = state[config.json_differential]
            
            if config.json_grace_time in state:
                # using grace_time setter to perform additional checks
                self.grace_time = state[config.json_grace_time]
            
            # validating new state
            try:
                self._has_been_validated = False
                self._validate()
            
            except:
                logger.debug('the new state is invalid, reverting to old state')
                raise
            
            finally:
                logger.debug('current status: {}'.format(self._status))
                logger.debug('temperatures: t0={t0}, tmin={tmin}, tmax={tmax}'.format(**self._temperatures))
                logger.debug('differential: {} deg'.format(self._differential))
                logger.debug('grace time: {} sec'.format(self._grace_time))
            
            self._last_update_timestamp = time.time()
            logger.debug('new internal state set')
    
    
    def _validate(self):
        """Validate the internal settings.
        
        A full validation is performed only if TimeTable._has_been_validated
        is not `True`, otherwise silently exits without errors.
        
        @exception jsonschema.ValidationError if internal settings are invalid
        """
        
        with self._lock:
            if not self._has_been_validated:
                
                # perform validation
                self.__getstate__()
                
                # if no exception is raised
                self._has_been_validated = True
    
    
    def settings(self, indent=0, sort_keys=True):
        """Get internal settings as JSON string.
        
        To adhere to the JSON standard, the `+Infinite` value of grace time is
        converted to `None`, thus it will be `null` in the returned JSON string.
        
        @exception jsonschema.ValidationError if internal settings are invalid
        """
        
        state = self.__getstate__()
        
        if not math.isfinite(state[config.json_grace_time]):
            state[config.json_grace_time] = None
        
        return json.dumps(state, indent=indent, sort_keys=sort_keys, allow_nan=False)
    
    
    # no need for @transactional because __setstate__ is @transactionl
    def load(self, settings):
        """Update internal state loading settings from JSON string.
        
        If the provided settings are invalid, the old state remains unchanged.
        
        @param settings the new settings (JSON-encoded string)
        
        @see thermod.config.json_schema for valid JSON schema
        @see TimeTable.__setstate__() for possible exceptions
            raised during storing of new settings
        """
        
        self.__setstate__(json.loads(settings, parse_constant=config.json_reject_invalid_float))
    
    
    # no need for @transactional because __setstate__ is @transactionl
    def reload(self):
        """Reload the timetable from JSON file.
        
        The JSON file is the same provided in TimeTable.__init__()
        method, thus if a different file is needed, set a new
        TimeTable.filepath to the full path before calling this method.
        
        If the JSON file is invalid (or `self.filepath` is not a string)
        an exception is raised and the internal settings remain unchanged.
        
        @exception RuntimeError if no timetable JSON file is provided
        @exception FileNotFoundError if the timetable JSON file cannot be found
        @exception PermissionError if the timetable JSON file cannot be read
        @exception OSError other filesystem-related errors in reading JSON file
        @exception ValueError if the timetable file is not in JSON format or
            the JSON content has syntax errors
        @exception jsonschema.ValidationError if the JSON content is not valid
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
                settings = json.load(file, parse_constant=config.json_reject_invalid_float)
                logger.debug('json file loaded')
            
            self.__setstate__(settings)
            self._last_update_timestamp = os.path.getmtime(self.filepath)
        
            logger.debug('timetable (re)loaded')
    
    
    def save(self, filepath=None):
        """Save the current timetable to JSON file.
        
        Save the current configuration of the timetable to the file
        pointed by `filepath` paramether (full path to file). If `filepath` is
        `None`, settings are saved to the internal TimeTable.filepath.
        
        @exception RuntimeError if no timetable JSON file is provided
        @exception jsonschema.ValidationError if internal settings are invalid
        @exception OSError if the file cannot be written or other OS related errors
        """
        
        logger.debug('saving timetable to file')
        
        if filepath is None:
            filepath = self.filepath
        
        with self._lock:
            logger.debug('lock acquired to save timetable')
            
            if not filepath:  # empty strings or None
                logger.debug('filepath not set, cannot save timetable')
                raise RuntimeError('no timetable file provided, cannot save data')
            
            # validate and retrive settings
            settings = self.__getstate__()
            
            # convert possible Infinite grace_time to None
            if math.isinf(settings[config.json_grace_time]):
                settings[config.json_grace_time] = None
            
            # if an old JSON file exist, load its content
            try:
                logger.debug('reading old JSON file {}'.format(filepath))
                with open(filepath, 'r') as file:
                    old_settings = json.load(file, parse_constant=config.json_reject_invalid_float)
            
            except FileNotFoundError:
                logger.debug('old JSON file does not exist, skipping')
                old_settings = None
            
            except JSONDecodeError:
                logger.debug('old JSON file is invalid, it will be overwrited')
                old_settings = None
            
            # save JSON settings
            with open(filepath, 'w') as file:
                try:
                    logger.debug('saving timetable to JSON file {}'.format(file.name))
                    json.dump(settings, file, indent=2, sort_keys=True, allow_nan=False)
                
                except:
                    logger.debug('cannot save new settings to filesystem')
                    
                    if old_settings:
                        logger.debug('restoring old settings')
                        json.dump(old_settings, file, indent=2, sort_keys=True, allow_nan=False)
                    
                    raise
        
            logger.debug('timetable saved')
    
    
    @property
    def lock(self):
        """Return the internal reentrant `threading.Condition` lock."""
        return self._lock
    
    
    def last_update_timestamp(self):
        """Return the timestamp of last settings update."""
        return self._last_update_timestamp
    
    
    def last_tgt_temp_reached_timestamp(self):
        """Return the POSIX timestamp when the target temperature was last reached."""
        return self._last_tgt_temp_reached_timestamp
    
    
    @property
    def status(self):
        """Return the current status."""
        with self._lock:
            logger.debug('lock acquired to get current status')
            return self._status
    
    
    @status.setter
    def status(self, status):
        """Set a new status."""
        with self._lock:
            logger.debug('lock acquired to set a new status')
            
            if status.lower() not in config.json_all_statuses:
                logger.debug('invalid new status: {}'.format(status))
                raise JsonValueError(
                    'the new status `{}` is invalid, it must be one of [{}]. '
                    'Falling back to the previous one: `{}`.'.format(
                        status,
                        ', '.join(config.json_all_statuses),
                        self._status))
            
            self._status = status.lower()
            
            # Note: cannot call _validate() method after simple update (like
            # this method, like tmax, t0, etc because those methods can be
            # used even to populate an empty TimeTable that is invalid till
            # a full population
            self._has_been_validated = False
            
            self._last_update_timestamp = time.time()
            logger.debug('new status set: {}'.format(self._status))
    
    
    @property
    def differential(self):
        """Return the current differential value."""
        with self._lock:
            logger.debug('lock acquired to get current differntial value')
            return self._differential
    
    
    @differential.setter
    def differential(self, value):
        """Set a new differential value."""
        with self._lock:
            logger.debug('lock acquired to set a new differential value')
            
            try:
                nvalue = config.temperature_to_float(value)
                
                if nvalue < 0 or nvalue > 1:
                    raise ValueError()
            
            # I catch and raise again the same exception to change the message
            except:
                logger.debug('invalid new differential value: {}'.format(value))
                raise JsonValueError(
                    'the new differential value `{}` is invalid, '
                    'it must be a number in range [0;1]'.format(value))
            
            self._differential = nvalue
            self._has_been_validated = False
            self._last_update_timestamp = time.time()
            logger.debug('new differential value set: {}'.format(nvalue))
    
    
    @property
    def grace_time(self):
        """Return the current grace time in *seconds*.
        
        The returned value is a float and can also be the positive infinity
        if the grace time has been disabled.
        """
        with self._lock:
            logger.debug('lock acquired to get current grace time')
            return self._grace_time
    
    
    @grace_time.setter
    def grace_time(self, seconds):
        """Set a new grace time in *seconds*.
        
        The input value must be a number or, to disable the grace time, the
        string `inf` or `infinity` (case insensitive). If the input is a
        float number it is rounded to the nearest integer value.
        """
        with self._lock:
            logger.debug('lock acquired to set a new grace time')
            
            try:
                nvalue = float(seconds is None and '+Inf' or seconds)
                
                if nvalue < 0:
                    raise ValueError()
                
                if math.isnan(nvalue):
                    nvalue = float('+Inf')
            
            except:
                logger.debug('invalid new grace time: {}'.format(seconds))
                raise JsonValueError(
                    'the new grace time `{}` is invalid, it must be a positive '
                    'number expressed in seconds or the string `Inf`'.format(seconds))
            
            self._grace_time = round(nvalue, 0)
            self._has_been_validated = False
            self._last_update_timestamp = time.time()
            logger.debug('new grace time set: {} sec'.format(self._grace_time))
    
    
    @property
    def t0(self):
        """Return the current value for ``t0`` temperature."""
        with self._lock:
            logger.debug('lock acquired to get current t0 temperature')
            return self._temperatures[config.json_t0_str]
    
    
    @t0.setter
    def t0(self, value):
        """Set a new value for ``t0`` temperature."""
        with self._lock:
            logger.debug('lock acquired to set a new t0 value')
            
            try:
                nvalue = config.temperature_to_float(value)
            
            # I catch and raise again the same exception to change the message
            except:
                logger.debug('invalid new value for t0 temperature: {}'.format(value))
                raise JsonValueError(
                    'the new value `{}` for t0 temperature '
                    'is invalid, it must be a number'.format(value))
            
            self._temperatures[config.json_t0_str] = nvalue
            self._has_been_validated = False
            self._last_update_timestamp = time.time()
            logger.debug('new t0 temperature set: {}'.format(nvalue))
    
    
    @property
    def tmin(self):
        """Return the current value for ``tmin`` temperature."""
        with self._lock:
            logger.debug('lock acquired to get current tmin temperature')
            return self._temperatures[config.json_tmin_str]
    
    
    @tmin.setter
    def tmin(self, value):
        """Set a new value for ``tmin`` temperature."""
        with self._lock:
            logger.debug('lock acquired to set a new tmin value')
            
            try:
                nvalue = config.temperature_to_float(value)
            
            # I catch and raise again the same exception to change the message
            except:
                logger.debug('invalid new value for tmin temperature: {}'.format(value))
                raise JsonValueError(
                    'the new value `{}` for tmin temperature '
                    'is invalid, it must be a number'.format(value))
            
            self._temperatures[config.json_tmin_str] = nvalue
            self._has_been_validated = False
            self._last_update_timestamp = time.time()
            logger.debug('new tmin temperature set: {}'.format(nvalue))
    
    
    @property
    def tmax(self):
        """Return the current value for ``tmax`` temperature."""
        with self._lock:
            logger.debug('lock acquired to get current tmax temperature')
            return self._temperatures[config.json_tmax_str]
    
    
    @tmax.setter
    def tmax(self, value):
        """Set a new value for ``tmax`` temperature."""
        with self._lock:
            logger.debug('lock acquired to set a new tmax value')
            
            try:
                nvalue = config.temperature_to_float(value)
            
            # I catch and raise again the same exception to change the message
            except:
                logger.debug('invalid new value for tmax temperature: {}'.format(value))
                raise JsonValueError(
                    'the new value `{}` for tmax temperature '
                    'is invalid, it must be a number'.format(value))
            
            self._temperatures[config.json_tmax_str] = nvalue
            self._has_been_validated = False
            self._last_update_timestamp = time.time()
            logger.debug('new tmax temperature set: {}'.format(nvalue))
    
    
    @property
    def heating(self):
        """Return the current heating interface."""
        with self._lock:
            logger.debug('lock acquired to get current heating interface')
            return self._heating
    
    
    @heating.setter
    def heating(self, heating):
        """Set a new heating interface.
        
        The `heating` must be a subclass of `thermod.heating.BaseHeating` class.
        """
        
        with self._lock:
            logger.debug('lock acquired to set new heating interface')
            
            if not isinstance(heating, BaseHeating):
                logger.debug('the heating must be a subclass of BaseHeating')
                raise TypeError('the heating must be a subclass of BaseHeating')
            
            if self._heating is not None:
                self._heating.release_resources()
            
            self._heating = heating
            logger.debug('new heating set')
    
    
    @property
    def thermometer(self):
        """Return the current thermometer interface."""
        with self._lock:
            logger.debug('lock acquired to get current thermometer interface')
            return self._thermometer
    
    
    @thermometer.setter
    def thermometer(self, thermometer):
        """Set a new thermometer interface.
        
        The `thermometer` must be a subclass of
        `thermod.thermometer.BaseThermometer` class.
        """
        
        with self._lock:
            logger.debug('lock acquired to set new thermometer interface')
            
            if not isinstance(thermometer, BaseThermometer):
                logger.debug('the thermometer must be a subclass of BaseThermometer')
                raise TypeError('the thermometer must be a subclass of BaseThermometer')
            
            if self._thermometer is not None:
                self._thermometer.release_resources()
            
            self._thermometer = thermometer
            logger.debug('new thermometer set')
    
    
    @transactional(exclude=['_lock', '_heating', '_thermometer'])
    def update(self, day, hour, quarter, temperature):
        """Update the target temperature in internal timetable."""
        # TODO scrivere documentazione
        logger.debug('updating timetable: day "{}", hour "{}", quarter "{}", '
                     'temperature "{}"'.format(day, hour, quarter, temperature))
        
        with self._lock:
            logger.debug('lock acquired to update a temperature in timetable')
            
            # get day name
            logger.debug('retriving day name')
            _day = config.json_get_day_name(day)
            
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
                raise JsonValueError('the provided quarter `{}` is not valid, '
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
            self._last_update_timestamp = time.time()
        
        logger.debug('timetable updated: day "{}", hour "{}", quarter "{}", '
                     'temperature "{}"'.format(_day, _hour, _quarter, _temp))
    
    
    @transactional(exclude=['_lock', '_heating', '_thermometer'])
    def update_days(self, json_data):
        """Update timetable for one or more days.
        
        The provided `json_data` must be a part of the whole JSON settings in
        `thermod.config.json_schema` containing all the informations for the
        days under update.
        """
        
        # TODO fare in modo che accetti sia JSON sia un dictonary con le info del giorno da aggiornare
        # TODO capire come mai pur essendo transactional è rimasta una gestione manuale per old_state
        
        logger.debug('updating timetable days')
        
        data = json.loads(json_data, parse_constant=config.json_reject_invalid_float)
        days = []
        
        if not isinstance(data, dict) or not data:
            logger.debug('cannot update timetable, the provided JSON data '
                         'is empty or invalid and doesn\'t contain any days')
            raise JsonValueError('the provided JSON data doesn\'t contain any days')
        
        with self._lock:
            logger.debug('lock acquired to update the following days {}'
                         .format(list(data.keys())))
            
            old_state = self.__getstate__()
            new_state = deepcopy(old_state)
            
            logger.debug('updating data for each provided day')
            for day, timetable in data.items():
                _day = config.json_get_day_name(day)
                new_state[config.json_timetable][_day] = timetable
                days.append(_day)
            
            try:
                self.__setstate__(new_state)
            except:
                logger.debug('cannot update timetable, reverting to old '
                             'settings, the provided JSON data is invalid: {}'
                             .format(json_data))
                self.__setstate__(old_state)
                raise
        
        return days
    
    
    def degrees(self, temperature):
        """Convert the name of a temperature in its corresponding number value.
        
        If temperature is already a number, the number itself is returned.
        
        @exception RuntimeError if the main temperatures aren't set yet
        @exception thermod.config.JsonValueError if the provided temperature is invalid
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
        
        logger.debug('temperature {!r} converted to {}'.format(temperature, value))
        
        return float(value)
    
    
    def target_temperature(self, target_time=None):
        """Return the target temperature at specific `target_time`.
        
        The specific `target_time` must be a 'datetime` object.
        
        If the current status is ON the returned value is float `+Inf`, if
        the current status is OFF the returned value is float `-Inf`.
        """
        
        if target_time is None:
            target_time = datetime.now()
        elif not isinstance(target_time, datetime):
            raise TypeError('target_temperature() requires a datetime object')
        
        target = None
        
        with self._lock:
            if self._status == config.json_status_on:  # always on
                target = float('+Inf')
            
            elif self._status == config.json_status_off:  # always off
                target = float('-Inf')
            
            elif self._status in config.json_all_temperatures:
                # target temperature is set manually
                target = self.degrees(self._temperatures[self._status])
                logger.debug('target_temperature: {}'.format(target))
            
            elif self._status == config.json_status_auto:
                # target temperature is retrived from timetable
                day = config.json_get_day_name(target_time.strftime('%w'))
                hour = config.json_format_hour(target_time.hour)
                quarter = int(target_time.minute // 15)
                
                target = self.degrees(self._timetable[day][hour][quarter])
                logger.debug('day: {}, hour: {}, quarter: {}, '
                             'target_temperature: {}'
                             .format(day, hour, quarter, target))
        
        return target
    
    
    def should_the_heating_be_on(self, room_temperature=None):
        """Check if the heating, now, should be on.
        
        If the provided temperature is `None` the thermometer interface is
        queried to retrive the current temperature.
        
        This method updates only the internal variable `self._last_tgt_temp_reached_timestamp`
        if appropriate conditions are met.
        
        @return an instance of thermod.timetable.ShouldBeOn with a boolean value
            of `True` if the heating should be on, `False` otherwise
        
        @see thermod.timetable.ShouldBeOn for additional attributes of this class
        
        @exception jsonschema.ValidationError if internal settings are invalid
        @exception thermod.thermometer.ThermometerError if an error happens
            while querying the therometer
        @exception thermod.config.JsonValueError if the provided room
            temperature is not a valid temperature
        """
        
        logger.debug('checking should-be status of the heating')
        
        should_be_on = None
        self._validate()
        
        with self._lock:
            logger.debug('lock acquired to check the should-be status')
            
            if room_temperature is None:
                room_temperature = self._thermometer.temperature
            
            target_time = datetime.now()
            
            target = None
            current = self.degrees(room_temperature)
            diff = self.degrees(self._differential)
            logger.debug('status: {}, room_temperature: {}, differential: {}'
                         .format(self._status, current, diff))
            
            if self._status == config.json_status_on:  # always on
                should_be_on = True
            
            elif self._status == config.json_status_off:  # always off
                should_be_on = False
            
            else:  # checking against current temperature and timetable
                target = self.target_temperature(target_time)
                ison = self._heating.is_on()
                nowts = target_time.timestamp()
                offts = self._heating.switch_off_time().timestamp()
                grace = self._grace_time
                
                if current >= target and nowts < self._last_tgt_temp_reached_timestamp:
                    # first time the target temp is reached, update timestamp
                    self._last_tgt_temp_reached_timestamp = nowts
                elif current < target:
                    self._last_tgt_temp_reached_timestamp = config.TIMESTAMP_MAX_VALUE
                
                tgtts = self._last_tgt_temp_reached_timestamp
                
                logger.debug('is_on: {}, switch_off_time: {}, tgt_temperature_time: {}, grace_time: {}'
                             .format(ison, datetime.fromtimestamp(offts), datetime.fromtimestamp(tgtts), grace))
                
                should_be_on = (
                    ((current <= (target - diff))
                    or ((current < target) and ((nowts - offts) > grace))
                    or ((current < (target + diff)) and ison))
                        and not (current >= target and (nowts - tgtts) > grace))
        
        logger.debug('the heating should be {}'
                     .format(should_be_on and 'ON' or 'OFF'))
        
        return ShouldBeOn(should_be_on, self._status, current, target)

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab