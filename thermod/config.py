# -*- coding: utf-8 -*-
"""Utilities, functions and constants for Thermod daemon."""

import os
import math
import calendar
import logging
import configparser

__date__ = '2015-09-13'
__updated__ = '2016-06-19'


# config module logger
logger = logging.getLogger(__name__)

# logger common settings
logger_base_name = 'thermod'
logger_fmt_msg = '{asctime},{msecs:03.0f} {name:19s} {levelname:8s} {message}'
logger_fmt_msg_syslog = '{name}[{process:d}]: {levelname} {message}'
logger_fmt_time = '%H:%M:%S'
logger_fmt_datetime = '%y-%m-%d %H:%M:%S'
logger_fmt_style = '{'

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

# socket default address and port
SOCKET_DEFAULT_HOST = 'localhost'
SOCKET_DEFAULT_PORT = 4344

# main config files and parsers
config_file = 'thermod.conf'
main_config_files = (config_file,
                     os.path.join(os.path.expanduser('~/.thermod'), config_file),
                     os.path.join('/usr/local/etc/thermod', config_file),
                     os.path.join('/etc/thermod', config_file))

def read_config_files(config_files=main_config_files):
    """Search and read main configuration files.
    
    @params config_files a list of possible path for configuration files
    @return a tuple with a configparser.ConfigParser object and an error code
        that can be used as POSIX return value (if no error occurred the error
        code is 0)
    """
    
    try:
        cfg = configparser.ConfigParser()
        logger.debug('searching main configuration in files {}'.format(config_files))
        
        _cfg_files_found = cfg.read(config_files) # TODO in caso di più file quale ha precedenza?
        
        if _cfg_files_found:
            logger.debug('configuration files found: {}'.format(_cfg_files_found))
        else:
            # manual managment of missing configuration file
            raise FileNotFoundError()
    
    except configparser.MissingSectionHeaderError as mshe:
        error_code = RET_CODE_CFG_FILE_SYNTAX_ERR
        logger.critical('invalid syntax in configuration file `%s`, '
                        'missing sections', mshe.source)
    
    except configparser.ParsingError as pe:
        error_code = RET_CODE_CFG_FILE_SYNTAX_ERR
        (_lineno, _line) = pe.errors[0]
        logger.critical('invalid syntax in configuration file `%s` at line %d: %s',
                        pe.source, _lineno, _line)
    
    except configparser.DuplicateSectionError as dse:
        error_code = RET_CODE_CFG_FILE_INVALID
        logger.critical('duplicate section `%s` in configuration file `%s`',
                        dse.section, dse.source)
    
    except configparser.DuplicateOptionError as doe:
        error_code = RET_CODE_CFG_FILE_INVALID
        logger.critical('duplicate option `%s` in section `%s` of configuration '
                        'file `%s`', doe.option, doe.section, doe.source)
    
    except configparser.Error as cpe:
        error_code = RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('parsing error in configuration file: `%s`', cpe)
    
    except FileNotFoundError:
        error_code = RET_CODE_CFG_FILE_MISSING
        logger.critical('no configuration files found in %s', config_files)
    
    except Exception as e:
        error_code = RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('unknown error in configuration file: `%s`', e)
    
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
    
    @return a tuple with the main settings: enabled, debug, timetable JSON file,
        check interval, scripts for thermometer and heating, socket host,
        socket port and error code; the error code can be used as POSIX return
        value, if no error occurred the error code is 0.
    
    @exception TypeError if cfg is not a configparser.ConfigParser object
    """
    
    if not isinstance(cfg, configparser.ConfigParser):
        raise TypeError('ConfigParser object required to parse main settings')
    
    try:
        # TODO finire controllo sui valori presenti nel file di config
        enabled = cfg.getboolean('global', 'enabled')
        debug = cfg.getboolean('global', 'debug')
        tt_file = cfg.get('global', 'timetable')
        interval = cfg.getint('global', 'interval')
        
        scripts = {'thermometer': cfg.get('scripts', 'thermometer'),
                   'on': cfg.get('scripts', 'switchon'),
                   'off': cfg.get('scripts', 'switchoff'),
                   'status': cfg.get('scripts', 'status')}
        
        host = cfg.get('socket', 'host', fallback=SOCKET_DEFAULT_HOST)
        port = cfg.getint('socket', 'port', fallback=SOCKET_DEFAULT_PORT)
            
        if (port < 0) or (port > 65535):
            # checking port here because the ControlThread is created after starting
            # the daemon and the resulting log file can be messy
            raise OverflowError('socket port {:d} is outside range 0-65535'.format(port))
    
    except configparser.NoSectionError as nse:
        error_code = RET_CODE_CFG_FILE_INVALID
        logger.critical('incomplete configuration file, missing `%s` section',
                        nse.section)
    
    except configparser.NoOptionError as noe:
        error_code = RET_CODE_CFG_FILE_INVALID
        logger.critical('incomplete configuration file, missing option `%s` '
                        'in section `%s`', noe.option, noe.section)
    
    except configparser.Error as cpe:
        error_code = RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('unknown error in configuration file: %s', cpe)
    
    except ValueError as ve:
        # raised by getboolean() and getint() methods
        error_code = RET_CODE_CFG_FILE_INVALID
        logger.critical('invalid configuration: {}'.format(ve))
    
    except OverflowError as oe:
        error_code = RET_CODE_CFG_FILE_INVALID
        logger.critical('invalid configuration: {}'.format(oe))
    
    except Exception as e:
        error_code = RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('unknown error in configuration file: {}'.format(e))
    
    except KeyboardInterrupt:
        error_code = RET_CODE_KEYB_INTERRUPT
    
    except:
        error_code = RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('unknown error in configuration file, no more details')
    
    else:
        error_code = RET_CODE_OK
        logger.debug('main settings parsed')
    
    return (enabled, debug, tt_file, interval, scripts, host, port, error_code)


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
                                 {'type': 'string', 'pattern': '[+]?[Ii][Nn][Ff]([Ii][Nn][Ii][Tt][Ii])?'}]},
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
            # is valid any real number
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
        # raise a ValueError
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

# vim: fileencoding=utf-8