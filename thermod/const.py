# -*- coding: utf-8 -*-
"""Constants of Thermod daemon.

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

import os
import sys
from datetime import datetime

__date__ = '2017-03-02'
__updated__ = '2017-03-02'


# logger common settings
LOGGER_BASE_NAME = 'thermod'
LOGGER_FMT_MSG = '{asctime},{msecs:03.0f} {name:19s} {levelname:8s} {message}'
LOGGER_FMT_MSG_SYSLOG = '{name}[{process:d}]: {levelname} {message}'
LOGGER_FMT_MSG_MAILLOG = '''\
Thermod daemon reported the following {levelname} alert:

{message}

Module: {name}
Date and time: {asctime}
'''
LOGGER_FMT_TIME = '%H:%M:%S'
LOGGER_FMT_DATETIME = '%Y-%m-%d %H:%M:%S'
LOGGER_FMT_STYLE = '{'

# return codes
RET_CODE_OK = 0
RET_CODE_DAEMON_DISABLED = 6
RET_CODE_PID_FILE_ERROR = 4
RET_CODE_CFG_FILE_MISSING = 10
RET_CODE_CFG_FILE_SYNTAX_ERR = 11
RET_CODE_CFG_FILE_INVALID = 12
RET_CODE_CFG_FILE_UNKNOWN_ERR = 13
RET_CODE_TT_NOT_FOUND = 20
RET_CODE_TT_READ_ERR = 21
RET_CODE_TT_INVALID_SYNTAX = 22
RET_CODE_TT_INVALID_CONTENT = 23
RET_CODE_TT_OTHER_ERR = 24
RET_CODE_PI_INIT_ERR = 25
RET_CODE_SCRIPT_INIT_ERR = 26
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

# socket default address and port
SOCKET_DEFAULT_HOST = 'localhost'
SOCKET_DEFAULT_PORT = 4344

# timestamp max value for current platform
try:
    _tmv = datetime(9999,12,31).timestamp()
except OverflowError:
    _tmv = sys.maxsize
finally:
    TIMESTAMP_MAX_VALUE = _tmv
    """Max value for a POSIX timestamp in current platform."""


# main config files and parsers
CONFIG_FILE = 'thermod.conf'
MAIN_CONFIG_FILES = (CONFIG_FILE,
                     os.path.join(os.path.expanduser('~/.thermod'), CONFIG_FILE),
                     os.path.join('/usr/local/etc/thermod', CONFIG_FILE),
                     os.path.join('/etc/thermod', CONFIG_FILE))


# thermod name convention (from json file)
JSON_STATUS = 'status'
JSON_TEMPERATURES = 'temperatures'
JSON_TIMETABLE = 'timetable'
JSON_DIFFERENTIAL = 'differential'
JSON_GRACE_TIME = 'grace_time'
JSON_ALL_SETTINGS = (JSON_STATUS, JSON_TEMPERATURES, JSON_TIMETABLE,
                     JSON_DIFFERENTIAL, JSON_GRACE_TIME)

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

# the keys of the following dict are the same number returned by %w of
# strftime(), while the names are used to avoid errors with different locales
JSON_DAYS_NAME_MAP = {1: 'monday',    '1': 'monday',
                      2: 'tuesday',   '2': 'tuesday',
                      3: 'wednesday', '3': 'wednesday',
                      4: 'thursday',  '4': 'thursday',
                      5: 'friday',    '5': 'friday',
                      6: 'saturday',  '6': 'saturday',
                      0: 'sunday',    '0': 'sunday'}

# full schema of JSON config file
JSON_SCHEMA = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'title': 'Timetable',
    'description': 'Timetable file for Thermod daemon',
    'type': 'object',
    'properties': {
        'status': {'enum': ['auto', 'on', 'off', 't0', 'tmin', 'tmax']},
        'differential': {'type': 'number', 'minimum': 0, 'maximum': 1},
        'grace_time': {'type': ['number', 'null'], 'minimum': 0},
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
            'additionalProperties': False}}
}

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab