# -*- coding: utf-8 -*-
"""Utilities, functions and constants for Thermod daemon."""

import os
import math
import calendar

__date__ = '2015-09-13'
__updated__ = '2016-03-28'


# paths to main config files
config_file = 'thermod.conf'
main_config_files = (config_file,
                     os.path.join(os.path.expanduser('~/.thermod'), config_file),
                     os.path.join('/usr/local/etc/thermod', config_file),
                     os.path.join('/etc/thermod', config_file))

# return codes
RET_CODE_OK = 0
RET_CODE_DAEMON_DISABLED = 3
RET_CODE_CFG_FILE_MISSING = 10
RET_CODE_CFG_FILE_SYNTAX_ERR = 11
RET_CODE_CFG_FILE_INVALID = 12
RET_CODE_CFG_FILE_UNKNOWN_ERR = 13
RET_CODE_TT_NOT_FOUND = 20
RET_CODE_TT_READ_ERR = 21
RET_CODE_TT_INVALID_SYNTAX = 22
RET_CODE_TT_INVALID_CONTENT = 23
RET_CODE_TT_OTHER_ERR = 24
RET_CODE_INIT_ERR = 29
RET_CODE_SOCKET_PORT_ERR = 30
RET_CODE_SOCKET_START_ERR = 31
RET_CODE_SOCKET_STOP_ERR = 32
RET_CODE_RUN_INVALID_STATE = 50
RET_CODE_RUN_INVALID_VALUE = 51
RET_CODE_RUN_HEATING_ERR = 52
RET_CODE_RUN_OTHER_ERR = 59
RET_CODE_SHUTDOWN_SWITCHOFF_ERR = 60
RET_CODE_SHUTDOWN_OTHER_ERR = 69
RET_CODE_KEYB_INTERRUPT = 130

# logger common settings
logger_base_name = 'thermod'
logger_fmt_msg = '{asctime},{msecs:03.0f} {name:19s} {levelname:8s} {message}'
logger_fmt_msg_syslog = '{name}[{process:d}]: {levelname} {message}'
logger_fmt_time = '%H:%M:%S'
logger_fmt_datetime = '%y-%m-%d %H:%M:%S'
logger_fmt_style = '{'

# thermod name convention (from json file)
json_status = 'status'
json_temperatures = 'temperatures'
json_timetable = 'timetable'
json_differential = 'differential'
json_grace_time = 'grace_time'
json_all_settings = (json_status, json_temperatures, json_timetable,
                     json_differential, json_grace_time)

json_t0_str = 't0'
json_tmin_str = 'tmin'
json_tmax_str = 'tmax'
json_all_temperatures = (json_t0_str, json_tmin_str, json_tmax_str)

json_status_on = 'on'
json_status_off = 'off'
json_status_auto = 'auto'
json_status_t0 = json_t0_str
json_status_tmin = json_tmin_str
json_status_tmax = json_tmax_str
json_all_statuses = (json_status_on, json_status_off, json_status_auto,
                     json_status_t0, json_status_tmin, json_status_tmax)

# the keys of the following dict are the same number returned by %w of
# strftime(), while the names are used to avoid errors with different locales
json_days_name_map = {1: 'monday',    '1': 'monday',
                      2: 'tuesday',   '2': 'tuesday',
                      3: 'wednesday', '3': 'wednesday',
                      4: 'thursday',  '4': 'thursday',
                      5: 'friday',    '5': 'friday',
                      6: 'saturday',  '6': 'saturday',
                      0: 'sunday',    '0': 'sunday'}

# full schema of JSON config file
json_schema = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'title': 'Timetable',
    'description': 'Timetable file for Thermod daemon',
    'type': 'object',
    'properties': {
        'status': {'enum': ['auto', 'on', 'off', 't0', 'tmin', 'tmax']},
        'differential': {'type': 'number', 'minimum': 0, 'maximum': 1},
        'grace_time': {'anyOf': [{'type': 'number', 'minimum': 0},
                                 {'type': 'string', 'pattern': '[+]?[Ii][Nn][Ff]'}]},
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
                '([01][0-9]|2[0-3])': {
                    'type': 'array',
                    'items': {'anyOf': [{'type': 'number'},
                                        {'type': 'string', 'pattern': '[-+]?[0-9]*\.?[0-9]+'},
                                        {'enum': ['t0', 'tmin', 'tmax']}]}}},
            'required': ['00', '01', '02', '03', '04', '05', '06', '07', '08', '09',
                         '10', '11', '12', '13', '14', '15', '16', '17', '18', '19',
                         '20', '21', '22', '23'],
            'additionalProperties': False}}
}


class JsonValueError(ValueError):
    """Exception for invalid settings values in JSON file or socket messages."""
    
    @property
    def message(self):
        return str(self)


class ScriptError(RuntimeError):
    """Handle error of an external script.
    
    Can be used in conjuction with other exceptions to store also the name
    of the external script that produced an error. This script name is never
    returned by default method, it must be requested manually.
    """
    
    def __init__(self, error=None, script=None):
        super().__init__(error)
        self.script = script


def is_valid_temperature(temperature):
    """Return True if the provided temperature is valid.
    
    A temperature is considered valid if it is a number or one of the
    following string values: 't0', 'tmin', 'tmax'. The positive/negative
    infinity and NaN are considered invalid.
    """
    
    result = None

    if temperature in json_all_temperatures:
        result = True
    else:
        try:
            t = float(temperature)
        except:
            result = False
        else:
            if not math.isinf(t) and not math.isnan(t):
                result = True
            else:
                result = False

    return result


def temperature_to_float(temperature):
    """Format the provided temperature as a float with one decimal.
    
    Can be used both for timetable and main temperatures in JSON file or for
    any other simple formatting. The input value must be a number except
    positive/negative infinity and NaN.
    
    @raise ValueError: if the provided temperature cannot be converted to float.
    """
    
    if not is_valid_temperature(temperature) or temperature in json_all_temperatures:
        raise ValueError('the provided temperature is not valid `{}`, '
                         'it must be a number'.format(temperature))
    
    return round(float(temperature), 1)


def json_format_temperature(temperature):
    """Format the provided temperature as a string for timetable JSON file.
    
    The output can be a number string with one single decimal (XX.Y) or
    one of the following string: 't0', 'tmin', 'tmax'.
    """
    
    result = None

    if is_valid_temperature(temperature):
        if temperature in json_all_temperatures:
            result = temperature
        else:
            # rounding returned value in order to avoid to many rapid changes
            # between on and off
            result = format(round(float(temperature), 1), '.1f')
    else:
        raise JsonValueError('the provided temperature is not valid `{}`, '
                             'it must be a number or one of the following '
                             'values: {}'.format(
                                    temperature,
                                    ', '.join(json_all_temperatures)))

    return result


def json_format_hour(hour):
    """Format the provided hour as a string in 24-hour clock with leading 0."""
    try:
        # if hour cannot be converted to int or is outside 0-23 range
        # raise a ValueError
        if int(float(hour)) not in range(24):
            raise Exception()
    except:
        raise JsonValueError('the provided hour is not valid `{}`, '
                             'it must be in range 0-23'.format(hour))

    return format(int(float(hour)), '0>2d')


def json_get_day_name(day):
    """Return the name of the provided day as used by Thermod.
    
    The input `day` can be a number in range 0-7 (0 and 7 are Sunday,
    1 is Monday, 2 is Tuesday, etc) or a day name in English or in the
    current locale.
    """
    
    result = None
    
    try:
        if day in json_days_name_map.keys():
            result = json_days_name_map[day]
        elif isinstance(day, int) and int(day) in range(8):
            result = json_days_name_map[int(day) % 7]
        elif str(day).lower() in set(json_days_name_map.values()):
            result = str(day).lower()
        else:
            day_name = [name.lower() for name in list(calendar.day_name)]
            day_abbr = [name.lower() for name in list(calendar.day_abbr)]
            
            if str(day).lower() in day_name:
                idx =  (day_name.index(str(day).lower())+1) % 7
                result = json_days_name_map[idx]
            elif str(day).lower() in day_abbr:
                idx =  (day_abbr.index(str(day).lower())+1) % 7
                result = json_days_name_map[idx]
            else:
                raise Exception
    
    except:
        raise JsonValueError('the provided day name or number `{}` is not valid'.format(day))
    
    return result

# vim: fileencoding=utf-8