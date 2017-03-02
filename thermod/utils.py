# -*- coding: utf-8 -*-
"""Utilities, functions and constants for Thermod daemon.

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
import math
import calendar
import logging
import configparser

from collections import namedtuple
from datetime import datetime

__date__ = '2015-09-13'
__updated__ = '2017-02-20'


# logger and its adapter
class LogStyleAdapter(logging.LoggerAdapter):
    """Format message with {}-arguments."""
    
    def __init__(self, logger, extra=None):
        super().__init__(logger, extra)
    
    def log(self, level, msg, *args, **kwargs):
        if self.isEnabledFor(level):
        
            kwa = {'extra': self.extra}
            for kw in ('exc_info', 'stack_info'):
                try:
                    kwa[kw] = kwargs[kw]
                except:
                    pass
            
            self.logger._log(level, msg.format(*args, **kwargs), (), **kwa)
    
    def addHandler(self, hdlr):
        self.logger.addHandler(hdlr)

logger = LogStyleAdapter(logging.getLogger(__name__))

# logger common settings
logger_base_name = 'thermod'
logger_fmt_msg = '{asctime},{msecs:03.0f} {name:19s} {levelname:8s} {message}'
logger_fmt_msg_syslog = '{name}[{process:d}]: {levelname} {message}'
logger_fmt_msg_maillog = '''\
Thermod daemon reported the following {levelname} alert:

{message}

Module: {name}
Date and time: {asctime}
'''
logger_fmt_time = '%H:%M:%S'
logger_fmt_datetime = '%Y-%m-%d %H:%M:%S'
logger_fmt_style = '{'

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
Settings = namedtuple('Settings', 'enabled, debug, tt_file, interval, heating, thermometer, host, port, email, error_code')
config_file = 'thermod.conf'
main_config_files = (config_file,
                     os.path.join(os.path.expanduser('~/.thermod'), config_file),
                     os.path.join('/usr/local/etc/thermod', config_file),
                     os.path.join('/etc/thermod', config_file))

def read_config_files(config_files=None):
    """Search and read main configuration files.
    
    @params config_files a list of possible path for configuration files
    @return a tuple with a configparser.ConfigParser object and an error code
        that can be used as POSIX return value (if no error occurred the error
        code is 0)
    """
    
    if config_files is None:
        config_files = main_config_files
    
    try:
        cfg = configparser.ConfigParser()
        logger.debug('searching main configuration in files {}', config_files)
        
        _cfg_files_found = cfg.read(config_files)
        
        if _cfg_files_found:
            logger.debug('configuration files found: {}', _cfg_files_found)
        else:
            # manual managment of missing configuration file
            raise FileNotFoundError()
    
    except configparser.MissingSectionHeaderError as mshe:
        error_code = RET_CODE_CFG_FILE_SYNTAX_ERR
        logger.critical('invalid syntax in configuration file `{}`, '
                        'missing sections', mshe.source)
    
    except configparser.ParsingError as pe:
        error_code = RET_CODE_CFG_FILE_SYNTAX_ERR
        (_lineno, _line) = pe.errors[0]
        logger.critical('invalid syntax in configuration file `{}` at line {:d}: {}',
                        pe.source, _lineno, _line)
    
    except configparser.DuplicateSectionError as dse:
        error_code = RET_CODE_CFG_FILE_INVALID
        logger.critical('duplicate section `{}` in configuration file `{}`',
                        dse.section, dse.source)
    
    except configparser.DuplicateOptionError as doe:
        error_code = RET_CODE_CFG_FILE_INVALID
        logger.critical('duplicate option `{}` in section `{}` of configuration '
                        'file `{}`', doe.option, doe.section, doe.source)
    
    except configparser.Error as cpe:
        error_code = RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('parsing error in configuration file: `{}`', cpe)
    
    except FileNotFoundError:
        error_code = RET_CODE_CFG_FILE_MISSING
        logger.critical('no configuration files found in {}', config_files)
    
    except Exception as e:
        error_code = RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('unknown error in configuration file: `{}`', e)
    
    except KeyboardInterrupt:
        error_code = RET_CODE_KEYB_INTERRUPT
    
    except:
        error_code = RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('unknown error in configuration file, no more details')
    
    else:
        error_code = RET_CODE_OK
        logger.debug('main configuration files read')
    
    return (cfg, error_code)

def parse_main_settings(cfg):
    """Parse configuration settings previously read.
    
    @params cfg configparser.ConfigParser object to parse data from
    
    @return a `Settings` tuple with the main settings and an error code
        that can be used as POSIX return value (if no error occurred the error
        code is 0)
    
    @exception TypeError if cfg is not a configparser.ConfigParser object
    """
    
    if not isinstance(cfg, configparser.ConfigParser):
        raise TypeError('ConfigParser object is required to parse main settings')
    
    logger.debug('parsing main settings')
    
    try:
        enabled = cfg.getboolean('global', 'enabled')
        debug = cfg.getboolean('global', 'debug')
        tt_file = cfg.get('global', 'timetable')
        interval = cfg.getint('global', 'interval')
        
        heating = {'manager': cfg.get('heating', 'heating')}
        if heating['manager'] == 'scripts':
            heating['on'] = cfg.get('heating/scripts', 'switchon')
            heating['off'] = cfg.get('heating/scripts', 'switchoff')
            heating['status'] = cfg.get('heating/scripts', 'status')
        
        elif heating['manager'] == 'PiPinsRelay':
            # The user choose to use the internal class for Raspberry Pi
            # heating instead of external scripts.
            
            _level = cfg.get('heating/PiPinsRelay', 'switch_on_level', fallback='high').casefold()
            if _level not in ('high', 'low'):
                raise ValueError('the switch_on_level must be `high` or `low`, '
                                 '`{}` provided'.format(_level))
            
            heating['pins'] = [int(p) for p in cfg.get('heating/PiPinsRelay', 'pins', fallback='').split(',')]
            heating['level'] = _level[0]  # only the first letter of _level is used
        
        # An `elif` can be added with additional specific heating classes
        # once they will be created.
        else:
            raise ValueError('invalid value `{}` for heating manager'.format(heating['manager']))
        
        thermometer = {'script': cfg.get('thermometer', 'thermometer')}
        if thermometer['script'][0] == '/':
            # If the first char is a / it denotes the beginning of a filesystem
            # path, so the value is acceptable and no additional parameters
            # are required.
            pass
        
        elif thermometer['script'] == 'PiAnalogZero':
            # The user choose to use the internal class for Raspberry Pi
            # thermometer instead of an external script.
            thermometer['channels'] = [int(c) for c in cfg.get('thermometer/PiAnalogZero', 'channels', fallback='').split(',')]
            thermometer['multiplier'] = cfg.getfloat('thermometer/PiAnalogZero', 'multiplier', fallback=1.0)
            thermometer['shift'] = cfg.getfloat('thermometer/PiAnalogZero', 'shift', fallback=0.0)
        
        # An `elif` can be added with additional specific thermometer classes
        # once they will be created.
        else:
            raise ValueError('invalid value `{}` for thermometer'.format(thermometer['script']))
        
        host = cfg.get('socket', 'host', fallback=SOCKET_DEFAULT_HOST)
        port = cfg.getint('socket', 'port', fallback=SOCKET_DEFAULT_PORT)
            
        if (port < 0) or (port > 65535):
            # checking port here because the ControlThread is created after starting
            # the daemon and the resulting log file can be messy
            raise OverflowError('socket port {:d} is outside range 0-65535'.format(port))
        
        eserver = cfg.get('email', 'server').split(':')
        euser = cfg.get('email', 'user', fallback='')
        epwd = cfg.get('email', 'password', fallback='')
        email = {'server': (len(eserver)>1 and (eserver[0], eserver[1]) or eserver[0]),
                 'sender': cfg.get('email', 'sender'),
                 'recipients': [rcpt for _,rcpt in cfg.items('email/rcpt')],
                 'subject': cfg.get('email', 'subject', fallback='Thermod alert'),
                 'credentials': ((euser or epwd) and (euser, epwd) or None)}
    
    except configparser.NoSectionError as nse:
        error_code = RET_CODE_CFG_FILE_INVALID
        logger.critical('incomplete configuration file, missing `{}` section', nse.section)
    
    except configparser.NoOptionError as noe:
        error_code = RET_CODE_CFG_FILE_INVALID
        logger.critical('incomplete configuration file, missing option `{}` '
                        'in section `{}`', noe.option, noe.section)
    
    except configparser.Error as cpe:
        error_code = RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('unknown error in configuration file: {}', cpe)
    
    except ValueError as ve:
        # Raised by getboolean(), getfloat(), getint() and int() methods
        # and if heating, switch_on_level or thermometer are not valid.
        error_code = RET_CODE_CFG_FILE_INVALID
        logger.critical('invalid configuration: {}', ve)
    
    except OverflowError as oe:
        error_code = RET_CODE_CFG_FILE_INVALID
        logger.critical('invalid configuration: {}', oe)
    
    except Exception as e:
        error_code = RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('unknown error in configuration file: {}', e)
    
    except KeyboardInterrupt:
        error_code = RET_CODE_KEYB_INTERRUPT
    
    except:
        error_code = RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('unknown error in configuration file, no more details')
    
    else:
        error_code = RET_CODE_OK
        logger.debug('main settings parsed')
    
    return Settings(enabled, debug, tt_file, interval, heating, thermometer, host, port, email, error_code)


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


def check_script(program):
    """Check the existence and executability of `program`.
    
    In case of error a `ScriptError` exception is raised.
    
    @param program the full path to the script to be checked
    @exception ScriptError if the script cannot be found or executed
    """
    
    if not os.path.isfile(program):
        raise ScriptError('file not found', program)
    
    if not os.access(program, os.X_OK):
        raise ScriptError('script not executable', program)


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
            # any real number is valid
            result = math.isfinite(t)

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
            # TODO capire come mai ho deciso di far tornare una stringa qui
            # e quindi capire come mai nella validazione del JSON accetto anche
            # stringhe che sono convertibili in float!
    else:
        raise JsonValueError('the provided temperature is not valid `{}`, '
                             'it must be a number or one of the following '
                             'values: {}'.format(
                                    temperature,
                                    ', '.join(json_all_temperatures)))

    return result


def json_format_hour(hour):
    """Format the provided hour as a string in 24H clock with a leading `h` and zeroes."""
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


def json_reject_invalid_float(value):
    """Used as parser for `Infinity` and `NaN` values in `json.loads()` module.
    
    Always rises an exception because `Infinity` and `NaN` are not accepted
    as valid values for numbers in Thermod.
    """
    
    raise JsonValueError('numbers must have finite values in JSON data, '
                         '`NaN` and `Infinity` are not accepted')

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab