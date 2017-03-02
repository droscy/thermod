# -*- coding: utf-8 -*-
"""Manage the timetable of Thermod.

Copyright (C) 2017 Simone Rossetto <simros85@gmail.com>

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

from . import utils, const
from .utils import JsonValueError, LogStyleAdapter
from .heating import BaseHeating
from .memento import transactional
from .thermometer import BaseThermometer, FakeThermometer

__date__ = '2015-09-09'
__updated__ = '2017-03-01'
__version__ = '1.5'

logger = LogStyleAdapter(logging.getLogger(__name__))



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
    
    def __init__(self, filepath=None):
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
        
        logger.debug('initializing {}', self.__class__.__name__)

        self._status = None
        self._temperatures = {}
        self._timetable = {}
        
        self._differential = 0.5
        self._grace_time = float('+Inf')  # disabled by default

        self._lock = Condition()
        """Provide single-thread concurrent access to methods of this class."""
        
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
        
        self._last_tgt_temp_reached_timestamp = const.TIMESTAMP_MAX_VALUE
        """Timestamp of target temperature last reaching.
        
        Whenever the target temperature is reached, this value is updated with
        the current timestamp. When the current temperature falls below the
        target temperature, this value is reset to `const.TIMESTAMP_MAX_VALUE`.
        
        It is used in the `TimeTable.should_the_heating_be_on()`
        method to respect the grace time.
        """
        
        self.filepath = filepath
        """Full path to a JSON timetable configuration file."""
        
        if self.filepath:
            self.reload()
    
    
    def __repr__(self, *args, **kwargs):
        return '{module}.{cls}({filepath!r})'.format(
                    module=self.__module__,
                    cls=self.__class__.__name__,
                    filepath=self.filepath)
    
    
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
    
        #new._lock = Condition()  # not needed a new _lock is in __init__ method
        
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
            
            settings = {const.JSON_STATUS: self._status,
                        const.JSON_DIFFERENTIAL: self._differential,
                        const.JSON_GRACE_TIME: self._grace_time,
                        const.JSON_TEMPERATURES: self._temperatures,
                        const.JSON_TIMETABLE: self._timetable}
            
            jsonschema.validate(settings, const.JSON_SCHEMA)
            logger.debug('the timetable is valid')
        
        logger.debug('returning internal state')
        return deepcopy(settings)
    
    
    @transactional(exclude=['_lock'])
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
            
            self._status = state[const.JSON_STATUS]
            self._temperatures = deepcopy(state[const.JSON_TEMPERATURES])
            self._timetable = deepcopy(state[const.JSON_TIMETABLE])
            
            if const.JSON_DIFFERENTIAL in state:
                self._differential = state[const.JSON_DIFFERENTIAL]
            
            if const.JSON_GRACE_TIME in state:
                # using grace_time setter to perform additional checks
                self.grace_time = state[const.JSON_GRACE_TIME]
            
            # validating new state
            try:
                self._has_been_validated = False
                self._validate()
            
            except:
                logger.debug('the new state is invalid, reverting to old state')
                raise
            
            finally:
                logger.debug('current status: {}', self._status)
                logger.debug('temperatures: t0={t0}, tmin={tmin}, tmax={tmax}', **self._temperatures)
                logger.debug('differential: {} deg', self._differential)
                logger.debug('grace time: {} sec', self._grace_time)
            
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
        
        if not math.isfinite(state[const.JSON_GRACE_TIME]):
            state[const.JSON_GRACE_TIME] = None
        
        return json.dumps(state, indent=indent, sort_keys=sort_keys, allow_nan=False)
    
    
    # no need for @transactional because __setstate__ is @transactionl
    def load(self, settings):
        """Update internal state loading settings from JSON string.
        
        If the provided settings are invalid, the old state remains unchanged.
        
        @param settings the new settings (JSON-encoded string)
        
        @see thermod.const.JSON_SCHEMA for valid JSON schema
        @see TimeTable.__setstate__() for possible exceptions
            raised during storing of new settings
        """
        
        self.__setstate__(json.loads(settings, parse_constant=utils.json_reject_invalid_float))
    
    
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
                logger.debug('loading json file: {}', self.filepath)
                settings = json.load(file, parse_constant=utils.json_reject_invalid_float)
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
            if math.isinf(settings[const.JSON_GRACE_TIME]):
                settings[const.JSON_GRACE_TIME] = None
            
            # if an old JSON file exist, load its content
            try:
                logger.debug('reading old JSON file {}', filepath)
                with open(filepath, 'r') as file:
                    old_settings = json.load(file, parse_constant=utils.json_reject_invalid_float)
            
            except FileNotFoundError:
                logger.debug('old JSON file does not exist, skipping')
                old_settings = None
            
            except JSONDecodeError:
                logger.debug('old JSON file is invalid, it will be overwrited')
                old_settings = None
            
            # save JSON settings
            with open(filepath, 'w') as file:
                try:
                    logger.debug('saving timetable to JSON file {}', file.name)
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
            
            if status.lower() not in const.JSON_ALL_STATUSES:
                logger.debug('invalid new status: {}', status)
                raise JsonValueError(
                    'the new status `{}` is invalid, it must be one of [{}]. '
                    'Falling back to the previous one: `{}`.'.format(
                        status,
                        ', '.join(const.JSON_ALL_STATUSES),
                        self._status))
            
            self._status = status.lower()
            
            # Note: cannot call _validate() method after simple update (like
            # this method, like tmax, t0, etc) because those updates can be
            # used even to populate an empty TimeTable that is invalid till
            # a full population
            self._has_been_validated = False
            
            self._last_update_timestamp = time.time()
            logger.debug('new status set: {}', self._status)
    
    
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
                nvalue = utils.temperature_to_float(value)
                
                if nvalue < 0 or nvalue > 1:
                    raise ValueError()
            
            # I catch and raise again the same exception to change the message
            except:
                logger.debug('invalid new differential value: {}', value)
                raise JsonValueError(
                    'the new differential value `{}` is invalid, '
                    'it must be a number in range [0;1]'.format(value))
            
            self._differential = nvalue
            self._has_been_validated = False
            self._last_update_timestamp = time.time()
            logger.debug('new differential value set: {}', nvalue)
    
    
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
        
        The input value must be a number or, to disable the grace time, one
        of the following values: `None` or the strings 'inf', 'infinity' or
        'nan' (case insensitive). If the input is a float number it is
        rounded to the nearest integer value.
        """
        with self._lock:
            logger.debug('lock acquired to set a new grace time')
            
            try:
                nvalue = float(seconds if seconds is not None else '+Inf')
                
                if nvalue < 0:
                    raise ValueError()
                
                if math.isnan(nvalue):
                    nvalue = float('+Inf')
            
            except:
                logger.debug('invalid new grace time: {}', seconds)
                raise JsonValueError(
                    'the new grace time `{}` is invalid, it must be a positive '
                    'number expressed in seconds or the string `Inf`'.format(seconds))
            
            self._grace_time = round(nvalue, 0)
            self._has_been_validated = False
            self._last_update_timestamp = time.time()
            logger.debug('new grace time set: {} sec', self._grace_time)
    
    
    @property
    def t0(self):
        """Return the current value for ``t0`` temperature."""
        with self._lock:
            logger.debug('lock acquired to get current t0 temperature')
            return self._temperatures[const.JSON_T0_STR]
    
    
    @t0.setter
    def t0(self, value):
        """Set a new value for ``t0`` temperature."""
        with self._lock:
            logger.debug('lock acquired to set a new t0 value')
            
            try:
                nvalue = utils.temperature_to_float(value)
            
            # I catch and raise again the same exception to change the message
            except:
                logger.debug('invalid new value for t0 temperature: {}', value)
                raise JsonValueError(
                    'the new value `{}` for t0 temperature '
                    'is invalid, it must be a number'.format(value))
            
            self._temperatures[const.JSON_T0_STR] = nvalue
            self._has_been_validated = False
            self._last_update_timestamp = time.time()
            logger.debug('new t0 temperature set: {}', nvalue)
    
    
    @property
    def tmin(self):
        """Return the current value for ``tmin`` temperature."""
        with self._lock:
            logger.debug('lock acquired to get current tmin temperature')
            return self._temperatures[const.JSON_TMIN_STR]
    
    
    @tmin.setter
    def tmin(self, value):
        """Set a new value for ``tmin`` temperature."""
        with self._lock:
            logger.debug('lock acquired to set a new tmin value')
            
            try:
                nvalue = utils.temperature_to_float(value)
            
            # I catch and raise again the same exception to change the message
            except:
                logger.debug('invalid new value for tmin temperature: {}', value)
                raise JsonValueError(
                    'the new value `{}` for tmin temperature '
                    'is invalid, it must be a number'.format(value))
            
            self._temperatures[const.JSON_TMIN_STR] = nvalue
            self._has_been_validated = False
            self._last_update_timestamp = time.time()
            logger.debug('new tmin temperature set: {}', nvalue)
    
    
    @property
    def tmax(self):
        """Return the current value for ``tmax`` temperature."""
        with self._lock:
            logger.debug('lock acquired to get current tmax temperature')
            return self._temperatures[const.JSON_TMAX_STR]
    
    
    @tmax.setter
    def tmax(self, value):
        """Set a new value for ``tmax`` temperature."""
        with self._lock:
            logger.debug('lock acquired to set a new tmax value')
            
            try:
                nvalue = utils.temperature_to_float(value)
            
            # I catch and raise again the same exception to change the message
            except:
                logger.debug('invalid new value for tmax temperature: {}', value)
                raise JsonValueError(
                    'the new value `{}` for tmax temperature '
                    'is invalid, it must be a number'.format(value))
            
            self._temperatures[const.JSON_TMAX_STR] = nvalue
            self._has_been_validated = False
            self._last_update_timestamp = time.time()
            logger.debug('new tmax temperature set: {}', nvalue)
    
    
    @transactional(exclude=['_lock'])
    def update(self, day, hour, quarter, temperature):
        """Update the target temperature in internal timetable."""
        # TODO scrivere documentazione
        logger.debug('updating timetable: day "{}", hour "{}", quarter "{}", '
                     'temperature "{}"', day, hour, quarter, temperature)
        
        with self._lock:
            logger.debug('lock acquired to update a temperature in timetable')
            
            # get day name
            logger.debug('retriving day name')
            _day = utils.json_get_day_name(day)
            
            # check hour validity
            logger.debug('checking and formatting hour')
            _hour = utils.json_format_hour(hour)
            
            # check validity of quarter of an hour
            logger.debug('checking validity of quarter')
            try:
                if int(float(quarter)) in range(4):
                    _quarter = int(float(quarter))
                else:
                    raise Exception()
            except:
                logger.debug('invalid quarter: {}', quarter)
                raise JsonValueError('the provided quarter `{}` is not valid, '
                                     'it must be in range 0-3'.format(quarter))
            
            # format temperature and check validity
            _temp = utils.json_format_temperature(temperature)
            
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
                     'temperature "{}"', _day, _hour, _quarter, _temp)
    
    
    # no need for @transactional because __setstate__ is @transactionl
    def update_days(self, json_data):
        """Update timetable for one or more days.
        
        The provided `json_data` must be a part of the whole JSON settings in
        `thermod.const.JSON_SCHEMA` containing all the informations for the
        days under update.
        
        @return the list of updated days
        @exception thermod.utils.JsonValueError if `json_data` is not valid
        @see TimeTable.__setstate__() for possible exceptions
            raised during storing of new settings
        """
        
        # TODO fare in modo che accetti sia JSON sia un dictonary con le info del giorno da aggiornare
        
        logger.debug('updating timetable days')
        
        data = json.loads(json_data, parse_constant=utils.json_reject_invalid_float)
        days = []
        
        if not isinstance(data, dict) or not data:
            logger.debug('cannot update timetable, the provided JSON data '
                         'is empty or invalid and doesn\'t contain any days')
            raise JsonValueError('the provided JSON data doesn\'t contain any days')
        
        with self._lock:
            logger.debug('lock acquired to update the following days {}', list(data.keys()))
            
            new_state = self.__getstate__()
            
            logger.debug('updating data for each provided day')
            for day, timetable in data.items():
                _day = utils.json_get_day_name(day)
                new_state[const.JSON_TIMETABLE][_day] = timetable
                days.append(_day)
            
            try:
                self.__setstate__(new_state)
            except:
                logger.debug('cannot update timetable, reverting to old '
                             'settings, the provided JSON data is invalid: {}',
                             json_data)
                raise
        
        return days
    
    
    def degrees(self, temperature):
        """Convert the name of a temperature in its corresponding number value.
        
        If temperature is already a number, the number itself is returned.
        
        @exception RuntimeError if the main temperatures aren't set yet
        @exception thermod.utils.JsonValueError if the provided temperature is invalid
        """
        
        logger.debug('converting temperature name to degrees')
        
        value = None
        
        with self._lock:
            logger.debug('lock acquired to convert temperature name')
            
            if not self._temperatures:
                logger.debug('no main temperature provided')
                raise RuntimeError('no main temperature provided, '
                                   'cannot convert name to degrees')
            
            temp = utils.json_format_temperature(temperature)
            
            if temp in const.JSON_ALL_TEMPERATURES:
                value = self._temperatures[temp]
            else:
                value = temp
        
        logger.debug('temperature {!r} converted to {}', temperature, value)
        
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
            if self._status == const.JSON_STATUS_ON:  # always on
                target = float('+Inf')
            
            elif self._status == const.JSON_STATUS_OFF:  # always off
                target = float('-Inf')
            
            elif self._status in const.JSON_ALL_TEMPERATURES:
                # target temperature is set manually
                target = self.degrees(self._temperatures[self._status])
                logger.debug('target_temperature: {}', target)
            
            elif self._status == const.JSON_STATUS_AUTO:
                # target temperature is retrived from timetable
                day = utils.json_get_day_name(target_time.strftime('%w'))
                hour = utils.json_format_hour(target_time.hour)
                quarter = int(target_time.minute // 15)
                
                target = self.degrees(self._timetable[day][hour][quarter])
                logger.debug('day: {}, hour: {}, quarter: {}, '
                             'target_temperature: {}', day, hour, quarter, target)
        
        return target
    
    
    # TODO spostare questo metodo fuori da TimeTable, direttamente nel binario
    # di thermod, in questo modo si dovrebbero disaccoppiare TimeTable,
    # BaseThermometer e BaseHeating.
    #
    # Si deve però controllare:
    #   - validità del TimeTable da ciclo di Thermod
    #   - impatti sul ControlSocket, che quindi deve essere aggiornato
    #
    # Si può quindi definire una lista di Monitor che vengono aggiornati ad
    # ogni ciclo di controllo (che si verifica anche quando viene cambiata
    # un'impostazione o da socket o da reload) oppure un thread a parte
    # che vai in wait all'infinito sul lock finché il lock non viene notificato.
    #
    # Da notare che la notifica del lock non necessariamente deve essere fatta
    # manualmente da ogni oggetto che modifica il TimeTable, ma si può creare
    # un decoratore che esegue "self._lock.notify()" ogni volta che quel
    # metodo finisce correttamente.
    def should_the_heating_be_on(self, current_temperature, heating_status, heating_switch_off_time):
        """Check if the heating, now, should be on.
        
        This method updates only the internal variable `self._last_tgt_temp_reached_timestamp`
        if appropriate conditions are met.
        
        @param current_temperature the current temperature of the room
        @param heating_status current status of the heating
        @param heating_switch_off_time the switch off time of the heating (must
            be a `datetime` object)
        
        @return an instance of thermod.timetable.ShouldBeOn with a boolean value
            of `True` if the heating should be on, `False` otherwise
        
        @see thermod.timetable.ShouldBeOn for additional attributes of this class
        
        @exception jsonschema.ValidationError if internal settings are invalid
        @exception thermod.thermometer.ThermometerError if an error happens
            while querying the therometer
        @exception thermod.thermometer.HeatingError if an error happens
            while querying the heating
        @exception thermod.utils.JsonValueError if the provided room
            temperature is not a valid temperature
        """
        
        logger.debug('checking should-be status of the heating')
        
        should_be_on = None
        self._validate()
        
        with self._lock:
            logger.debug('lock acquired to check the should-be status')
            
            target_time = datetime.now()
            
            target = None
            current = self.degrees(current_temperature)
            diff = self.degrees(self._differential)
            logger.debug('status: {}, current_temperature: {}, differential: {}',
                         self._status, current, diff)
            
            if self._status == const.JSON_STATUS_ON:  # always on
                should_be_on = True
            
            elif self._status == const.JSON_STATUS_OFF:  # always off
                should_be_on = False
            
            else:  # checking against current temperature and timetable
                target = self.target_temperature(target_time)
                ison = bool(heating_status)
                nowts = target_time.timestamp()
                offts = heating_switch_off_time.timestamp()
                grace = self._grace_time
                
                if current >= target and nowts < self._last_tgt_temp_reached_timestamp:
                    # first time the target temp is reached, update timestamp
                    self._last_tgt_temp_reached_timestamp = nowts
                elif current < target:
                    self._last_tgt_temp_reached_timestamp = const.TIMESTAMP_MAX_VALUE
                
                tgtts = self._last_tgt_temp_reached_timestamp
                
                logger.debug('heating_on: {}, switch_off_time: {}, tgt_temperature_time: {}, grace_time: {}',
                             ison, datetime.fromtimestamp(offts), datetime.fromtimestamp(tgtts), grace)
                
                should_be_on = (
                    ((current <= (target - diff))
                    or ((current < target) and ((nowts - offts) > grace))
                    or ((current < (target + diff)) and ison))
                        and not (current >= target and (nowts - tgtts) > grace))
        
        logger.debug('the heating should be {}', (should_be_on and 'ON' or 'OFF'))
        
        return ShouldBeOn(should_be_on, self._status, current, target)

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab