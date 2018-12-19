# -*- coding: utf-8 -*-
"""Manage the timetable of Thermod.

Copyright (C) 2018 Simone Rossetto <simros85@gmail.com>

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

import os
import json
import logging
import jsonschema
import time
import math
import calendar

from copy import deepcopy
from datetime import datetime
from json.decoder import JSONDecodeError

from .common import LogStyleAdapter, ThermodStatus, TIMESTAMP_MAX_VALUE, JsonValueError
from .memento import transactional

__date__ = '2015-09-09'
__updated__ = '2018-12-19'
__version__ = '1.10'

logger = LogStyleAdapter(logging.getLogger(__name__))


# Common names for timetable and socket messages fields.
JSON_STATUS = 'status'
JSON_TEMPERATURES = 'temperatures'
JSON_TIMETABLE = 'timetable'
JSON_DIFFERENTIAL = 'differential'
JSON_GRACE_TIME = 'grace_time'
JSON_COOLING = 'cooling'
JSON_ALL_SETTINGS = (JSON_STATUS, JSON_TEMPERATURES, JSON_TIMETABLE,
                     JSON_DIFFERENTIAL, JSON_GRACE_TIME, JSON_COOLING)

JSON_T0_STR = 't0'
JSON_TMIN_STR = 'tmin'
JSON_TMAX_STR = 'tmax'
JSON_ALL_TEMPERATURES = (JSON_T0_STR, JSON_TMIN_STR, JSON_TMAX_STR)

JSON_STATUS_ON = 'on'
JSON_STATUS_OFF = 'off'
JSON_STATUS_AUTO = 'auto'
JSON_STATUS_T0 = JSON_T0_STR
JSON_STATUS_TMIN = JSON_TMIN_STR
JSON_STATUS_TMAX = JSON_TMAX_STR
JSON_ALL_STATUSES = (JSON_STATUS_ON, JSON_STATUS_OFF, JSON_STATUS_AUTO,
                     JSON_STATUS_T0, JSON_STATUS_TMIN, JSON_STATUS_TMAX)

# The keys of the following dict are the same numbers returned by %w of
# strftime(), while the names are used to avoid errors with different locales.
JSON_DAYS_NAME_MAP = {1: 'monday',    '1': 'monday',
                      2: 'tuesday',   '2': 'tuesday',
                      3: 'wednesday', '3': 'wednesday',
                      4: 'thursday',  '4': 'thursday',
                      5: 'friday',    '5': 'friday',
                      6: 'saturday',  '6': 'saturday',
                      0: 'sunday',    '0': 'sunday'}

# Full schema for JSON timetable file.
JSON_SCHEMA = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'title': 'Timetable',
    'description': 'Timetable file for Thermod daemon',
    'type': 'object',
    'properties': {
        'status': {'enum': ['auto', 'on', 'off', 't0', 'tmin', 'tmax']},
        'differential': {'type': 'number', 'minimum': 0, 'maximum': 1},
        'grace_time': {'type': ['number', 'null'], 'minimum': 0},
        'cooling': {'type': 'boolean'},
        'temperatures': {
            'type': 'object',
            'properties': {
                't0': {'type': 'number'},
                'tmin': {'type': 'number'},
                'tmax': {'type': 'number'}},
            'required': ['t0', 'tmin', 'tmax'],
            'additionalProperties': False},
        'timetable': {
            'type': 'object',
            'properties': {
                'monday': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]},
                'tuesday': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]},
                'wednesday': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]},
                'thursday': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]},
                'friday': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]},
                'saturday': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]},
                'sunday': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]}},
            'required': ['monday', 'tuesday', 'wednesday', 'thursday',
                         'friday', 'saturday', 'sunday'],
            'additionalProperties': False}},
    'required': ['status', 'temperatures', 'timetable'],
    'additionalProperties': False,
    'definitions': {
        'day': {
            'patternProperties': {
                'h([01][0-9]|2[0-3])': {
                    'type': 'array',
                    'items': {'anyOf': [{'type': 'number'},
                                        {'type': 'string', 'pattern': '[-+]?[0-9]*\.?[0-9]+'},
                                        {'enum': ['t0', 'tmin', 'tmax']}]}}},
            'required': ['h00', 'h01', 'h02', 'h03', 'h04', 'h05', 'h06', 'h07', 'h08', 'h09',
                         'h10', 'h11', 'h12', 'h13', 'h14', 'h15', 'h16', 'h17', 'h18', 'h19',
                         'h20', 'h21', 'h22', 'h23'],
            'additionalProperties': False}}}



def is_valid_temperature(temperature):
    """Return `True` if the provided temperature is valid.
    
    A temperature is considered valid if it is a number or one of the
    string values in `thermod.config.JSON_ALL_TEMPERATURES`.
    The positive/negative infinity and NaN are considered invalid.
    """
    
    result = None

    if temperature in JSON_ALL_TEMPERATURES:
        result = True
    else:
        try:
            t = float(temperature)
        except:
            result = False
        else:
            # any real number is valid
            result = math.isfinite(t)

    return result


def temperature_to_float(temperature):
    """Format the provided temperature as a float with one decimal.
    
    Can be used both for timetable and main temperatures in JSON file or for
    any other simple formatting. The input value must be a number except
    positive/negative infinity and NaN.
    
    @exception ValueError if the provided temperature cannot be converted to float.
    """
    
    if not is_valid_temperature(temperature) or temperature in JSON_ALL_TEMPERATURES:
        raise ValueError('the temperature `{}` is not valid, '
                         'it must be a number'.format(temperature))
    
    return round(float(temperature), 1)


def json_format_temperature(temperature):
    """Format the provided temperature as a string for timetable JSON file.
    
    The output can be a number string with one single decimal (XX.Y) or
    one of the following string: 't0', 'tmin', 'tmax'.
    """
    
    result = None
    
    if is_valid_temperature(temperature):
        if temperature in JSON_ALL_TEMPERATURES:
            result = temperature
        else:
            # rounding returned value in order to avoid to many rapid changes
            # between on and off
            result = format(round(float(temperature), 1), '.1f')
            # TODO capire come mai ho deciso di far tornare una stringa qui
            # e quindi capire come mai nella validazione del JSON accetto anche
            # stringhe che sono convertibili in float!
    else:
        raise JsonValueError('the provided temperature is not valid `{}`, '
                             'it must be a number or one of the following '
                             'values: {}'.format(
                                    temperature,
                                    ', '.join(JSON_ALL_TEMPERATURES)))
    
    return result


def json_format_hour(hour):
    """Format the provided hour as a string in 24H clock with a leading `h` and zeroes.
    
    @exception thermod.timetable.JsonValueError if the `hour` cannot be formatted
    """
    try:
        # if hour cannot be converted to int or is outside 0-23 range
        # raise a JsonValueError
        _hour = int(float(str(hour).lstrip('h')))
        if _hour not in range(24):
            raise Exception()
    except:
        raise JsonValueError('the provided hour is not valid `{}`, '
                             'it must be in range 0-23 with an optional '
                             'leading `h`'.format(hour))
    
    return 'h{:0>2d}'.format(_hour)


def json_get_day_name(day):
    """Return the name of the provided day as used by Thermod.
    
    The input `day` can be a number in range 0-7 (0 and 7 are Sunday,
    1 is Monday, 2 is Tuesday, etc) or a day name in English or in the
    current locale.
    
    @exception thermod.timetable.JsonValueError if the `day` is invalid
    """
    
    result = None
    
    try:
        if day in JSON_DAYS_NAME_MAP.keys():
            result = JSON_DAYS_NAME_MAP[day]
        elif isinstance(day, int) and int(day) in range(8):
            result = JSON_DAYS_NAME_MAP[int(day) % 7]
        elif str(day).lower() in set(JSON_DAYS_NAME_MAP.values()):
            result = str(day).lower()
        else:
            day_name = [name.lower() for name in list(calendar.day_name)]
            day_abbr = [name.lower() for name in list(calendar.day_abbr)]
            
            if str(day).lower() in day_name:
                idx =  (day_name.index(str(day).lower())+1) % 7
                result = JSON_DAYS_NAME_MAP[idx]
            elif str(day).lower() in day_abbr:
                idx =  (day_abbr.index(str(day).lower())+1) % 7
                result = JSON_DAYS_NAME_MAP[idx]
            else:
                raise Exception
    
    except:
        raise JsonValueError('the provided day name or number `{}` is not valid'.format(day))
    
    return result


def json_reject_invalid_float(value):
    """Used as parser for `Infinity` and `NaN` values in `json.loads()` function.
    
    Always raises `thermod.timetable.JsonValueError` exception because
    `Infinity` and `NaN` are not accepted as valid values for numbers in
    Thermod daemon.
    """
    
    raise JsonValueError('numbers must have finite values in JSON data, '
                         '`NaN` and `Infinity` are not accepted')



class ShouldBeOn(int):
    """Behaves as a boolean with a Thermod status attribute."""
    
    def __new__(cls, should_be_on, *args, **kwargs):
        return int.__new__(cls, bool(should_be_on))
    
    def __init__(self, should_be_on, status=None):
        self.status = status
    
    def __repr__(self, *args, **kwargs):
        return '<{module}.{cls}({should!r}, {status!r})>'.format(
                    module=self.__module__,
                    cls=self.__class__.__name__,
                    should=bool(self),
                    status=self.status)
    
    def __str__(self, *args, **kwargs):
        return str(bool(self))
    
    @property
    def should_be_on(self):
        return bool(self)



class TimeTable(object):
    """Represent the timetable to control the heating."""
    
    def __init__(self, filepath=None, mode=1):
        """Init the timetable.
        
        The timetable can be initialized empty, if `filepath` is `None`,
        or with full information to control the real heating providing the
        path to the JSON timetable file.

        @param filepath full path to a JSON file that contains all the
            informations to setup the timetable
        @param mode the working mode regarding switch-on and switch-off
            temperatures due to thermal inertia
        
        @see TimeTable.reload() for possible exceptions
        """
        
        logger.debug('initializing {}', self.__class__.__name__)

        self._status = None
        self._temperatures = {}
        self._timetable = {}
        
        self._mode = mode
        self._differential = 0.5
        self._grace_time = float('+Inf')  # disabled by default
        self._cooling = False
        
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
        
        Equal to JSON file mtime if settings are loaded from file or equal
        to current timestamp of last settings change.
        """
        
        self._last_tgt_temp_reached_timestamp = TIMESTAMP_MAX_VALUE
        """Timestamp of target temperature last reaching.
        
        Whenever the target temperature is reached, this value is updated with
        the current timestamp. When the current temperature falls below the
        target temperature, this value is reset to `common.TIMESTAMP_MAX_VALUE`.
        
        It is used in the `TimeTable.should_the_heating_be_on()`
        method to respect the grace time.
        """
        
        self._last_below_tgt_temp_timestamp = TIMESTAMP_MAX_VALUE
        """Timestamp of current temperature last fall below target temperature.
        
        Whenever the current temperature falls below the target temperature
        this value is updated with the current timestamp. It is reset to
        `common.TIMESTAMP_MAX_VALUE` when the current temperature reaches
        the target temperature.
        
        It is used in the `TimeTable.should_the_heating_be_on()`
        method to respect the grace time.
        """
        
        self.filepath = filepath
        """Full path to a JSON timetable configuration file."""
        
        if self.filepath:
            self.reload()
    
    
    def __repr__(self, *args, **kwargs):
        return '<{module}.{cls}({filepath!r}, {mode!r})>'.format(
                    module=self.__module__,
                    cls=self.__class__.__name__,
                    filepath=self.filepath,
                    mode=self._mode)
    
    
    def __eq__(self, other):
        """Check if two TimeTable objects have the same settings.
        
        The check is performed only on `status`, main `temperatures`,
        `timetable`, `differential`, `grace time` and `mode` values
        because the other attributes are relative to the specific
        usage of the TimeTable object.
        
        @param other the other TimeTable to be compared
        """
        
        try:
            result = (isinstance(other, self.__class__)
                        and (self._status == other._status)
                        and (self._temperatures == other._temperatures)
                        and (self._timetable == other._timetable)
                        and (self._mode == other._mode)
                        and (self._differential == other._differential)
                        and (self._grace_time == other._grace_time)
                        and (self._cooling == other._cooling))
        
        except AttributeError:
            result = False
        
        return result
    
    
    def __copy__(self):
        """Return a <em>shallow copy</em> of this TimeTable."""
        
        new = self.__class__()
        
        new._status = self._status
        new._temperatures = self._temperatures
        new._timetable = self._timetable
        new._mode = self._mode
        new._differential = self._differential
        new._grace_time = self._grace_time
        new._cooling = self._cooling
        
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
        new._mode = self._mode
        new._differential = self._differential
        new._grace_time = self._grace_time
        new._cooling = self._cooling
        
        new._has_been_validated = self._has_been_validated
        new._last_update_timestamp = self._last_update_timestamp
        new._last_tgt_temp_reached_timestamp = self._last_tgt_temp_reached_timestamp
        
        new.filepath = self.filepath
        
        return new
    
    
    def __getstate__(self):
        """Return the internal state as a dictonary.
        
        The returned dictonary is a deep copy of the internal state.
        The validation is performed only if `TimeTable._has_been_validated`
        is `False`.
        
        @exception jsonschema.ValidationError if the validation has been
            performed and internal state is invalid.
        """
        
        logger.debug('retrieving internal state')
            
        settings = {JSON_STATUS: self._status,
                    JSON_DIFFERENTIAL: self._differential,
                    JSON_GRACE_TIME: self._grace_time,
                    JSON_COOLING: self._cooling,
                    JSON_TEMPERATURES: self._temperatures,
                    JSON_TIMETABLE: self._timetable}
        
        if not self._has_been_validated:
            logger.debug('performing validation')
            jsonschema.validate(settings, JSON_SCHEMA)
        
        logger.debug('the timetable is valid, returning internal state')
        return deepcopy(settings)
    
    
    @transactional()
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
        
        self._status = state[JSON_STATUS]
        self._temperatures = deepcopy(state[JSON_TEMPERATURES])
        self._timetable = deepcopy(state[JSON_TIMETABLE])
        
        if JSON_DIFFERENTIAL in state:
            self._differential = state[JSON_DIFFERENTIAL]
        
        if JSON_GRACE_TIME in state:
            # using grace_time setter to perform additional checks
            self.grace_time = state[JSON_GRACE_TIME]
        
        if JSON_COOLING in state:
            self._cooling = state[JSON_COOLING]
        
        self._last_update_timestamp = time.time()
        
        # validating new state
        try:
            self._has_been_validated = False
            self._validate()
        
        except:
            logger.debug('the new state is invalid, reverting to old state')
            raise
        
        finally:
            # TODO with exceptions the transactional fires later than this code
            # block, thus these debug messages will contain the new values, always!
            logger.debug('current status: {}', self._status)
            logger.debug('temperatures: t0={t0}, tmin={tmin}, tmax={tmax}', **self._temperatures)
            logger.debug('differential: {} deg', self._differential)
            logger.debug('grace time: {} sec', self._grace_time)
            logger.debug('cooling: {}', self._cooling)
        
        logger.debug('new internal state set')
    
    
    def _validate(self):
        """Validate the internal settings.
        
        A full validation is performed only if `TimeTable._has_been_validated`
        is `False` , otherwise silently exits without errors.
        
        @exception jsonschema.ValidationError if the validation has been
            performed and internal state is invalid.
        """
        
        if not self._has_been_validated:
            
            # perform validation
            self.__getstate__()
            
            # if no exception is raised
            self._has_been_validated = True
    
    
    def settings(self, indent=0, sort_keys=False):
        """Get internal settings as JSON string.
        
        To adhere to the JSON standard, the `+Infinite` value of grace time is
        converted to `None`, thus it will be `null` in the returned JSON string.
        
        @exception ValueError if there is an invalid float in internal settings
        """
        
        state = self.__getstate__()
        
        if not math.isfinite(state[JSON_GRACE_TIME]):
            state[JSON_GRACE_TIME] = None
        
        return json.dumps(state, indent=indent, sort_keys=sort_keys, allow_nan=False)
    
    
    # no need for @transactional because __setstate__ is @transactionl
    def load(self, settings):
        """Update internal state loading settings from JSON string.
        
        If the provided settings are invalid, the old state remains unchanged.
        
        @param settings the new settings (JSON-encoded string)
        
        @see thermod.JSON_SCHEMA for valid JSON schema
        @see TimeTable.__setstate__() for possible exceptions
            raised during storing of new settings
        """
        
        self.__setstate__(json.loads(settings, parse_constant=json_reject_invalid_float))
    
    
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
            
        if not self.filepath:  # empty string or None
            logger.debug('filepath not set, cannot continue')
            raise RuntimeError('no timetable file provided, cannot (re)load data')
        
        # loading json file
        with open(self.filepath, 'r') as file:
            logger.debug('loading json file: {}', self.filepath)
            settings = json.load(file, parse_constant=json_reject_invalid_float)
            logger.debug('json file loaded')
        
        self.__setstate__(settings)
        self._last_update_timestamp = os.path.getmtime(self.filepath)
        
        logger.debug('timetable (re)loaded')
    
    
    def save(self, filepath=None):
        """Save the current timetable to JSON file.
        
        Save the current configuration of the timetable to the file
        pointed by `filepath` paramether (full path to file). If `filepath` is
        `None`, settings are saved to the internal TimeTable.filepath.
        
        @exception ValueError if there is a 'NaN' or 'Infinite' float in internal settings
        @exception RuntimeError if no timetable JSON file is provided
        @exception jsonschema.ValidationError if internal settings are invalid
        @exception OSError if the file cannot be written or other OS related errors
        """
        
        logger.debug('saving timetable to file')
        
        if filepath is None:
            filepath = self.filepath
            
        if not filepath:  # empty string or None
            logger.debug('filepath not set, cannot save timetable')
            raise RuntimeError('no timetable file provided, cannot save data')
        
        # validate (if not already validated) and retrive settings
        #self._has_been_validated = False
        settings = self.__getstate__()
        
        # convert possible Infinite grace_time to None
        if not math.isfinite(settings[JSON_GRACE_TIME]):
            settings[JSON_GRACE_TIME] = None
        
        # if an old JSON file exists, load its content for later restore if necessary
        try:
            logger.debug('reading old JSON file {}', filepath)
            with open(filepath, 'r') as file:
                old_settings = json.load(file, parse_constant=json_reject_invalid_float)
        
        except FileNotFoundError:
            logger.debug('old JSON file does not exist, skipping')
            old_settings = None
        
        except JSONDecodeError:
            logger.debug('old JSON file is invalid, it will be overwritten')
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
    
    
    def last_update_timestamp(self):
        """Return the timestamp of last settings update."""
        return self._last_update_timestamp
    
    
    def last_tgt_temp_reached_timestamp(self):
        """Return the POSIX timestamp when the target temperature was last reached."""
        return self._last_tgt_temp_reached_timestamp
    
    
    @property
    def status(self):
        """Return the current status."""
        logger.debug('reading current status')
        return self._status
    
    
    @status.setter
    def status(self, status):
        """Set a new status."""
        
        logger.debug('setting a new status')
        
        if status.lower() not in JSON_ALL_STATUSES:
            logger.debug('invalid new status: {}', status)
            raise JsonValueError(
                'the new status `{}` is invalid, it must be one of [{}]. '
                'Falling back to the previous one: `{}`.'.format(
                    status,
                    ', '.join(JSON_ALL_STATUSES),
                    self._status))
        
        self._status = status.lower()
        self._last_update_timestamp = time.time()
        logger.debug('new status set: {}', self._status)
    
    
    @property
    def differential(self):
        """Return the current differential value."""
        logger.debug('reading current differntial value')
        return self._differential
    
    
    @differential.setter
    def differential(self, value):
        """Set a new differential value."""
        
        logger.debug('setting a new differential value')
        
        try:
            nvalue = temperature_to_float(value)
            
            if nvalue < 0 or nvalue > 1:
                raise ValueError()
        
        # I catch and raise again the same exception to change the message
        except:
            logger.debug('invalid new differential value: {}', value)
            raise JsonValueError(
                'the new differential value `{}` is invalid, '
                'it must be a number in range [0;1]'.format(value))
        
        self._differential = nvalue
        self._last_update_timestamp = time.time()
        logger.debug('new differential value set: {}', nvalue)
    
    
    @property
    def grace_time(self):
        """Return the current grace time in *seconds*.
        
        The returned value is a float and can also be the positive infinity
        if the grace time has been disabled.
        """
        logger.debug('reading current grace time')
        return self._grace_time
    
    
    @grace_time.setter
    def grace_time(self, seconds):
        """Set a new grace time in *seconds*.
        
        The input value must be a positive number or, to disable the grace time,
        one of the following values: `None` or the strings 'Inf', 'Infinity' or
        'NaN' (case insensitive). If the input is a float number it is
        rounded to the nearest integer value.
        """
        
        logger.debug('setting a new grace time')
        
        try:
            nvalue = float(seconds if seconds is not None else '+Inf')
            
            if math.isnan(nvalue):
                nvalue = float('+Inf')
            
            if nvalue < 0:
                raise ValueError()
        
        except:
            logger.debug('invalid new grace time: {}', seconds)
            raise JsonValueError(
                'the new grace time `{}` is invalid, it must be a positive '
                'number expressed in seconds or the string `Inf`'.format(seconds))
        
        self._grace_time = round(nvalue, 0)
        self._last_update_timestamp = time.time()
        logger.debug('new grace time set: {} sec', self._grace_time)
    
    
    @property
    def cooling(self):
        """Return `True` if currently the cooling system is used instead of heating.
        
        If this is `True` the `TimeTable.should_the_heating_be_on()` method
        behaves differently: when the temperature if over target it returns `True`.
        """
        
        logger.debug('checking if system is in cooling mode: {}', self._cooling)
        return self._cooling
    
    
    @cooling.setter
    def cooling(self, value):
        """Set to `True` if `TimeTable.should_the_heating_be_on()` must
        return `True` when the temperature is over target."""
        
        logger.debug('setting the new cooling value')
        
        if value == True or value == False:
            self._cooling = value
        
        else:
            logger.debug('invalid new cooling setting: {}', value)
            raise JsonValueError('the new cooling setting `{}` is invalid, '
                                'it must be a boolean'.format(value))
        
        self._last_update_timestamp = time.time()
        logger.debug('new cooling value set: {}', self._cooling)
    
    
    @property
    def t0(self):
        """Return the current value for ``t0`` temperature."""
        logger.debug('reading current t0 temperature')
        return self._temperatures[JSON_T0_STR]
    
    
    @t0.setter
    def t0(self, value):
        """Set a new value for ``t0`` temperature."""
        
        logger.debug('setting a new t0 value')
        
        try:
            nvalue = temperature_to_float(value)
        
        # I catch and raise again the same exception to change the message
        except:
            logger.debug('invalid new value for t0 temperature: {}', value)
            raise JsonValueError(
                'the new value `{}` for t0 temperature '
                'is invalid, it must be a number'.format(value))
        
        self._temperatures[JSON_T0_STR] = nvalue
        self._last_update_timestamp = time.time()
        logger.debug('new t0 temperature set: {}', nvalue)
    
    
    @property
    def tmin(self):
        """Return the current value for ``tmin`` temperature."""
        logger.debug('reading current tmin temperature')
        return self._temperatures[JSON_TMIN_STR]
    
    
    @tmin.setter
    def tmin(self, value):
        """Set a new value for ``tmin`` temperature."""
        
        logger.debug('setting a new tmin value')
        
        try:
            nvalue = temperature_to_float(value)
        
        # I catch and raise again the same exception to change the message
        except:
            logger.debug('invalid new value for tmin temperature: {}', value)
            raise JsonValueError(
                'the new value `{}` for tmin temperature '
                'is invalid, it must be a number'.format(value))
        
        self._temperatures[JSON_TMIN_STR] = nvalue
        self._last_update_timestamp = time.time()
        logger.debug('new tmin temperature set: {}', nvalue)
    
    
    @property
    def tmax(self):
        """Return the current value for ``tmax`` temperature."""
        logger.debug('reading current tmax temperature')
        return self._temperatures[JSON_TMAX_STR]
    
    
    @tmax.setter
    def tmax(self, value):
        """Set a new value for ``tmax`` temperature."""
        
        logger.debug('setting a new tmax value')
        
        try:
            nvalue = temperature_to_float(value)
        
        # I catch and raise again the same exception to change the message
        except:
            logger.debug('invalid new value for tmax temperature: {}', value)
            raise JsonValueError(
                'the new value `{}` for tmax temperature '
                'is invalid, it must be a number'.format(value))
        
        self._temperatures[JSON_TMAX_STR] = nvalue
        self._last_update_timestamp = time.time()
        logger.debug('new tmax temperature set: {}', nvalue)
    
    
    @transactional()
    def update(self, day, hour, quarter, temperature):
        """Update the target temperature in internal timetable.
        
        @param day the day to be updated
        @param hour the hour to be updated
        @param quarter the quarter to be updated
        @param temperature the new temperature to set in the timetable
            for the provided day, hour and quarter
        
        @exception JsonValueError if the provided quarter is not valid
        """
        
        logger.debug('updating timetable: day "{}", hour "{}", quarter "{}", '
                     'temperature "{}"', day, hour, quarter, temperature)
            
        # get day name
        logger.debug('retrieving day name')
        _day = json_get_day_name(day)
        
        # check hour validity
        logger.debug('checking and formatting hour')
        _hour = json_format_hour(hour)
        
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
        logger.debug('checking and formatting temperature')
        _temp = json_format_temperature(temperature)
        
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
    
    
    def degrees(self, temperature):
        """Convert the name of a temperature in its corresponding number value.
        
        If temperature is already a number, the number itself is returned.
        
        @exception RuntimeError if the main temperatures aren't set yet
        @exception thermod.timetable.JsonValueError if the provided temperature
            is invalid
        """
        
        logger.debug('converting temperature name to degrees')
        
        if not self._temperatures:
            logger.debug('no main temperature provided')
            raise RuntimeError('no main temperature provided, '
                               'cannot convert name to degrees')
        
        value = json_format_temperature(temperature)
        
        if value in JSON_ALL_TEMPERATURES:
            value = self._temperatures[value]
        
        logger.debug('temperature {!r} converted to {}', temperature, value)
        
        return float(value)
    
    
    def target_temperature(self, target_time=None):
        """Return the target temperature at specific `target_time`.
        
        NB: when `self._cooling` is `True`, `tmax` and `tmin` values are
        inverted because those values are used with the meaning of ON and OFF,
        so when the set temperature is `tmax` it means both "heating on" and
        "cooling on".
        
        @param target_time must be a `datetime` object
        @return the target temperature at specific `target_time`, if the
            current status is ON or OFF the returned value is `None`.
        """
        
        if target_time is None:
            target_time = datetime.now()
        elif not isinstance(target_time, datetime):
            try:
                target_time = datetime.fromtimestamp(target_time)
            except TypeError:
                raise TypeError('target_temperature() requires a datetime '
                                'object or a float timestamp, `{}` given'
                                .format(target_time))
        
        logger.debug('getting target temperature for {}', target_time)
        
        target = None  # default value for always ON or OFF
        
        if self._status in JSON_ALL_TEMPERATURES:
            # target temperature is set manually
            target = self.degrees(self._temperatures[self._status])
            logger.debug('target_temperature: {}', target)
        
        elif self._status == JSON_STATUS_AUTO:
            # target temperature is retrived from timetable
            day = json_get_day_name(target_time.strftime('%w'))
            hour = json_format_hour(target_time.hour)
            quarter = int(target_time.minute // 15)
            
            target = self._timetable[day][hour][quarter]
            
            # in case of cooling, the meaning of tmax and tmin are inverted
            if self._cooling:
                if target == JSON_TMAX_STR:
                    target = JSON_TMIN_STR
                elif target == JSON_TMIN_STR:
                    target = JSON_TMAX_STR
            
            target = self.degrees(target)
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
    def should_the_heating_be_on(self, current_temperature, heatcool_status):
        """Check if the heating/cooling, now, should be on.
        
        This method can be used with both heating and cooling. What makes the
        difference in behaviour is the internal value of `TimeTable._cooling`
        attribute: if it is `True` this method returns `True` when the current
        temperature is above target, otherwise when the temperature is below
        target.
        
        This method updates only the internal variable `self._last_tgt_temp_reached_timestamp`
        if appropriate conditions are met.
        
        @param current_temperature the current temperature of the room
        @param heatcool_status current status of the heating/cooling (as
            returned from `BaseHeating.status` or `BaseCooling.status`)
        
        @return an instance of ShouldBeOn with a boolean value
            of `True` if the heating/cooling should be on, `False` otherwise
        
        @see ShouldBeOn for additional attributes of this class
        
        @exception jsonschema.ValidationError if internal settings are invalid
        @exception JsonValueError if the provided room temperature is not a
            valid temperature
        """
        
        logger.debug('checking should-be status of the {}',
                     ('heating' if not self._cooling else 'cooling system'))
        
        should_be_on = None
        self._validate()
        
        target_time = datetime.now()
        
        realtgt = None
        current = self.degrees(current_temperature)
        diff = self.degrees(self._differential)
        logger.debug('status: {}, current_temperature: {}, differential: {}',
                     self._status, current, diff)
        
        if self._status == JSON_STATUS_ON:  # always on
            should_be_on = True
        
        elif self._status == JSON_STATUS_OFF:  # always off
            should_be_on = False
        
        else:  # checking against current temperature and timetable
            
            # the real target temperature get from timetable
            realtgt = self.target_temperature(target_time)
            
            # The working mode simply adjusts the real target temperature and
            # differential values to take into account thermal inertia.
            if self._mode == 1:
                # heating: switch on at target-diff, switch off at target+diff
                # cooling: switch on at target+diff, switch off at target-diff
                target = realtgt
            
            elif self._mode == 2:
                if not self._cooling:
                    # switch on at target-2*diff, switch off at target
                    target = realtgt - diff
                
                else:
                    # switch on at target+2*diff, switch off at target
                    target = realtgt + diff
                    
            elif self._mode == 3:
                diff /= 2
                
                if not self._cooling:
                    # switch on at target-2*diff, switch off at target-diff
                    target = realtgt - 3*diff
                
                else:
                    # switch on at target+2*diff, switch off at target+diff
                    target = realtgt + 3*diff
                    
            else:
                logger.warning('invalid working mode "{}", fallback to default mode "1"', self._mode)
                target = realtgt
            
            ison = bool(heatcool_status)
            nowts = target_time.timestamp()
            grace = self._grace_time
            
            if current >= target and nowts < self._last_tgt_temp_reached_timestamp:
                # first time the target temp is reached, update timestamp
                self._last_tgt_temp_reached_timestamp = nowts
            elif current < target:
                self._last_tgt_temp_reached_timestamp = TIMESTAMP_MAX_VALUE
            
            if current < target and nowts < self._last_below_tgt_temp_timestamp:
                # first time the current temp has fallen below target temp, update timestamp
                self._last_below_tgt_temp_timestamp = nowts
            elif current >= target:
                self._last_below_tgt_temp_timestamp = TIMESTAMP_MAX_VALUE
            
            tgtts = self._last_tgt_temp_reached_timestamp
            bltts = self._last_below_tgt_temp_timestamp
            
            logger.debug('{}_on: {}, below_tgt_temperature_time: {}, '
                         'tgt_temperature_time: {}, grace_time: {}',
                         ('heating' if not self._cooling else 'cooling'),
                         ison, datetime.fromtimestamp(bltts),
                         datetime.fromtimestamp(tgtts), grace)
            
            if not self._cooling:
                should_be_on = (
                    ((current <= (target - diff))
                    or ((current < target) and ((nowts - bltts) > grace))
                    or ((current < (target + diff)) and ison))
                        and not (current >= target and (nowts - tgtts) > grace))
            
            else:
                # In case of cooling system the meaning of tgtts and bltts are inverted
                # the same way are inverted the major/minor signs.
                should_be_on = (
                    ((current >= (target + diff))
                    or ((current > target) and ((nowts - tgtts) > grace))
                    or ((current > (target - diff)) and ison))
                        and not (current <= target and (nowts - bltts) > grace))
        
        logger.debug('the {} should be {}',
                     ('heating' if not self._cooling else 'cooling system'),
                     ('ON' if should_be_on else 'OFF'))
        
        return ShouldBeOn(should_be_on,
                          ThermodStatus(target_time.timestamp(),
                                        self._status,
                                        self._cooling,
                                        heatcool_status,
                                        current,
                                        realtgt))

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
