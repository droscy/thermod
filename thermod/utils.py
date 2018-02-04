# -*- coding: utf-8 -*-
"""Utilities and common functions for Thermod daemon.

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
import math
import calendar

from .common import ScriptError
from .timetable import JsonValueError, JSON_ALL_TEMPERATURES, JSON_DAYS_NAME_MAP

__date__ = '2015-09-13'
__updated__ = '2017-03-04'


def check_script(program):
    """Check the existence and executability of `program`.
    
    In case of error a `ScriptError` exception is raised.
    
    @param program the full path to the script to be checked
    @exception thermod.common.ScriptError if the script cannot be found or executed
    """
    
    if not os.path.isfile(program):
        raise ScriptError('file not found', program)
    
    if not os.access(program, os.X_OK):
        raise ScriptError('script not executable', program)


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

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
