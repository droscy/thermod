# -*- coding: utf-8 -*-
"""Constants and functions about main configuration file.

This module is only useful in main Thermod daemon because it doesn't raise any
exception and uses logger to print info and error messages. 

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
import logging
import configparser
from collections import namedtuple

from . import common

__date__ = '2015-09-13'
__updated__ = '2019-04-20'

logger = common.LogStyleAdapter(logging.getLogger(__name__))


# Global variable to use fake implementations of Raspberry Pi hardware.
_fake_RPi_Heating = False
_fake_RPi_Thermometer = False


# Main config filename, search paths, classes and parsers.
MAIN_CONFIG_FILENAME = 'thermod.conf'
MAIN_CONFIG_FILES = (MAIN_CONFIG_FILENAME,
                     os.path.join(os.path.expanduser('~/.thermod'), MAIN_CONFIG_FILENAME),
                     os.path.join('/usr/local/etc/thermod', MAIN_CONFIG_FILENAME),
                     os.path.join('/etc/thermod', MAIN_CONFIG_FILENAME))


Settings = namedtuple('Settings', ['enabled', 'debug', 'tt_file', 'interval',
                                   'scale', 'inertia', 'heating', 'cooling',
                                   'thermometer', 'host', 'port', 'email'])
"""Tuple used to transfer settings from config file to main daemon."""


def read_config_file(config_files=None):
    """Search and read main configuration file.
    
    @param config_files a list of possible path for configuration file
    @return a tuple with a configparser.ConfigParser object and an error code
        that can be used as POSIX return value (if no error occurred the error
        code is 0)
    """
    
    if config_files is None:
        config_files = MAIN_CONFIG_FILES
    
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
        error_code = common.RET_CODE_CFG_FILE_SYNTAX_ERR
        logger.critical('invalid syntax in configuration file `{}`, '
                        'missing sections', mshe.source)
    
    except configparser.ParsingError as pe:
        error_code = common.RET_CODE_CFG_FILE_SYNTAX_ERR
        (_lineno, _line) = pe.errors[0]
        logger.critical('invalid syntax in configuration file `{}` at line {:d}: {}',
                        pe.source, _lineno, _line)
    
    except configparser.DuplicateSectionError as dse:
        error_code = common.RET_CODE_CFG_FILE_INVALID
        logger.critical('duplicate section `{}` in configuration file `{}`',
                        dse.section, dse.source)
    
    except configparser.DuplicateOptionError as doe:
        error_code = common.RET_CODE_CFG_FILE_INVALID
        logger.critical('duplicate option `{}` in section `{}` of configuration '
                        'file `{}`', doe.option, doe.section, doe.source)
    
    except configparser.Error as cpe:
        error_code = common.RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('parsing error in configuration file: `{}`', cpe)
    
    except FileNotFoundError:
        error_code = common.RET_CODE_CFG_FILE_MISSING
        logger.critical('no configuration files found in {}', config_files)
    
    except Exception as e:
        error_code = common.RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('unknown error in configuration file: `{}`', e)
    
    except KeyboardInterrupt:
        error_code = common.RET_CODE_KEYB_INTERRUPT
    
    except:
        error_code = common.RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('unknown error in configuration file, no more details')
    
    else:
        error_code = common.RET_CODE_OK
        logger.debug('main configuration files read')
    
    return (cfg, error_code)


def parse_main_settings(cfg):
    """Parse configuration settings previously read.
    
    @param cfg configparser.ConfigParser object to parse data from
    
    @return a tuple with two elements: the first is a `thermod.utils.Settings`
        tuple with the just parsed main settings, the second is the error
        code that can be used as POSIX return value (if no error occurred the
        error code is 0)
    
    @exception TypeError if cfg is not a configparser.ConfigParser object
    """
    
    if not isinstance(cfg, configparser.ConfigParser):
        raise TypeError('ConfigParser object is required to parse main settings')
    
    try:
        # parsing main settings
        logger.debug('parsing main settings')
        enabled = cfg.getboolean('global', 'enabled')
        debug = cfg.getboolean('global', 'debug')
        tt_file = cfg.get('global', 'timetable')
        interval = cfg.getint('global', 'interval')
        
        # reading inertia value
        try:
            # in Thermod version 1.x the inertia name was 'mode'
            inertia = cfg.getint('global', 'mode')
            
            # if no exception raised, print a warning message
            logger.warning('deprecated option `mode` in configuration file, '
                           'please rename it to `inertia`')
        
        # if exception, no old settings found, so read the right 'inertia' value
        except configparser.NoOptionError as noe:
            inertia = cfg.getint('global', 'inertia', fallback=1)
        
        # parsing working scale
        _scale = cfg.get('global', 'scale', fallback='celsius').casefold()
        if _scale not in ('celsius', 'fahrenheit'):
            raise ValueError('the working degree scale must be `celsius` or '
                             '`fahrenheit`, `{}` provided'.format(_scale))
        
        scale = _scale[0]  # only the first letter of _scale is used
        
        # parsing heating settings
        logger.debug('parsing heating settings')
        heating = {'manager': cfg.get('heating', 'heating')}
        
        if heating['manager'] not in ('scripts', 'PiPinsRelay'):
            raise ValueError('invalid value `{}` for heating'.format(heating['manager']))
        
        heating['on'] = cfg.get('heating/scripts', 'switchon')
        heating['off'] = cfg.get('heating/scripts', 'switchoff')
        heating['status'] = cfg.get('heating/scripts', 'status', fallback=None)
        
        if heating['status'] == '':
            heating['status'] = None
        
        _level = cfg.get('heating/PiPinsRelay', 'switch_on_level', fallback='high').casefold()
        if _level not in ('high', 'low'):
            raise ValueError('the switch_on_level for heating must be `high` '
                             'or `low`, `{}` provided'.format(_level))
        
        heating['pins'] = [int(p) for p in cfg.get('heating/PiPinsRelay', 'pins', fallback='').split(',')]
        heating['level'] = _level[0]  # only the first letter of _level is used
        
        # parsing cooling settings
        logger.debug('parsing cooling settings')
        cooling = {'manager': cfg.get('cooling', 'cooling', fallback='')}
        
        if cooling['manager'] == '':
            cooling['manager'] = None
        
        elif cooling['manager'] not in ('heating', 'scripts', 'PiPinsRelay'):
            raise ValueError('invalid value `{}` for cooling system'.format(cooling['manager']))
            
        cooling['on'] = cfg.get('cooling/scripts', 'switchon')
        cooling['off'] = cfg.get('cooling/scripts', 'switchoff')
        cooling['status'] = cfg.get('cooling/scripts', 'status', fallback=None)
        
        if cooling['status'] == '':
            cooling['status'] = None
        
        _level = cfg.get('cooling/PiPinsRelay', 'switch_on_level', fallback='high').casefold()
        if _level not in ('high', 'low'):
            raise ValueError('the switch_on_level for cooling must be `high` '
                             'or `low`, `{}` provided'.format(_level))
        
        cooling['pins'] = [int(p) for p in cfg.get('cooling/PiPinsRelay', 'pins', fallback='').split(',')]
        cooling['level'] = _level[0]  # only the first letter of _level is used
        
        # parsing thermometer setting
        logger.debug('parsing thermometer settings')
        _t_ref = cfg.get('thermometer', 't_ref')
        _t_raw = cfg.get('thermometer', 't_raw')
        thermometer = {'thermometer': cfg.get('thermometer', 'thermometer'),
                       'calibration': cfg.getboolean('thermometer', 'calibration', fallback=False),
                       't_ref': [float(t) for t in _t_ref.split(',')] if _t_ref else [],
                       't_raw': [float(t) for t in _t_raw.split(',')] if _t_raw else [],
                       'similcheck': cfg.getboolean('thermometer', 'similarity_check', fallback=True),
                       'simillen': cfg.getint('thermometer', 'similarity_queuelen', fallback=12),
                       'simildelta': cfg.getfloat('thermometer', 'similarity_delta', fallback=3.0),
                       # The avgtask is disabled by default for backward compatibility
                       # in case the user is using and old config file.
                       'avgtask': cfg.getboolean('thermometer', 'avgtask', fallback=False),
                       'avgint': cfg.getint('thermometer', 'avgint', fallback=3),
                       'avgtime': cfg.getint('thermometer', 'avgtime', fallback=6),
                       'avgskip': cfg.getfloat('thermometer', 'avgskip', fallback=0.33),
                       'stddev': cfg.getfloat('thermometer', 'stddev', fallback=2.0)}
        
        if thermometer['thermometer'][0] != '/' and thermometer['thermometer'] not in ('PiAnalogZero', '1Wire'):
            # If the first char is a / it denotes the beginning of a filesystem
            # path, so the value is acceptable. If the path is not a valid
            # script, the error will be managed later.
            raise ValueError('invalid value `{}` for thermometer'.format(thermometer['thermometer']))
        
        if thermometer['simillen'] < 1:
            raise ValueError('advanced parameter `similarity_queuelen` must be a positive integer')
        
        if thermometer['simildelta'] <= 0:
            raise ValueError('advanced parameter `similarity_delta` must be a positive number')
        
        _scale = cfg.get('thermometer', 'scale', fallback='celsius').casefold()
        if _scale not in ('celsius', 'fahrenheit'):
                raise ValueError('the degree scale of the thermometer must be '
                                 '`celsius` or `fahrenheit`, `{}` provided'.format(_scale))
        
        thermometer['scale'] = _scale[0]  # only the first letter of _scale is used
        
        thermometer['az'] = {}
        thermometer['az']['channels'] = [int(c) for c in cfg.get('thermometer/PiAnalogZero', 'channels', fallback='').split(',')]
        thermometer['az']['stddev'] = cfg.getfloat('thermometer/PiAnalogZero', 'stddev', fallback=2.0)
        
        thermometer['w1'] = {}
        thermometer['w1']['devices'] = [dev.strip() for dev in cfg.get('thermometer/1Wire', 'devices', fallback='').split(',')]
        thermometer['w1']['stddev'] = cfg.getfloat('thermometer/1Wire', 'stddev', fallback=2.0)
        
        if thermometer['az']['stddev'] <= 0:
            raise ValueError('advanced parameter `stddev` for PiAnalogZero must be positive')
        
        if thermometer['w1']['stddev'] <= 0:
            raise ValueError('advanced parameter `stddev` for 1Wire must be positive')
        
        if thermometer['thermometer'] == 'PiAnalogZero':
            # In version 1.0.0 of Thermod the PiAnalogZero thermometer made use
            # of a class-builtin averaging task so, now that the averaging task
            # is a separate decorator, we enable it by default unless the user
            # has manually disabled it in the config file.
            thermometer['avgtask'] = cfg.getboolean('thermometer', 'avgtask', fallback=True)
            
            # For backward compatibility of PiAnalogZero section in Thermod 1.0.0
            # we check if the config file still have older settings: realint,
            # avgtime and skipval.
            if thermometer['avgtask']:
                thermometer['avgint'] = cfg.getint('thermometer/PiAnalogZero', 'realint', fallback=thermometer['avgint'])
                thermometer['avgtime'] = cfg.getint('thermometer/PiAnalogZero', 'avgtime', fallback=thermometer['avgtime'])
                thermometer['avgskip'] = cfg.getfloat('thermometer/PiAnalogZero', 'skipval', fallback=thermometer['avgskip'])
        
        # Checking here the avg* settings because they can have been overwritten
        # by older settings of PiAnalogZero section.
        if thermometer['avgint'] < 1:
            raise ValueError('advanced parameter `avgint` must be at least 1 second')
        
        if thermometer['avgtime'] < (2*interval/60):
            raise ValueError('advanced parameter `avgtime` must be at least {:d} minutes'.format(2 * interval / 60))
        
        if thermometer['avgskip'] < 0 or thermometer['avgskip'] > 1:
            raise ValueError('advanced parameter `avgskip` must be a float number between 0 and 1')
        
        # parsing socket settings
        logger.debug('parsing socket settings')
        host = cfg.get('socket', 'host', fallback=common.SOCKET_DEFAULT_HOST)
        port = cfg.getint('socket', 'port', fallback=common.SOCKET_DEFAULT_PORT)
            
        if (port < 0) or (port > 65535):
            # checking port here because the ControlThread is created after starting
            # the daemon and the resulting log file can be messy
            raise OverflowError('socket port {:d} is outside range 0-65535'.format(port))
        
        # parsing email settings
        logger.debug('parsing email settings')
        eserver = cfg.get('email', 'server').split(':')
        euser = cfg.get('email', 'user', fallback='')
        epwd = cfg.get('email', 'password', fallback='')
        email = {'server': ((eserver[0], eserver[1]) if len(eserver)>1 else eserver[0]),
                 'sender': cfg.get('email', 'sender'),
                 'recipients': [rcpt for (_, rcpt) in cfg.items('email/rcpt')],
                 'subject': cfg.get('email', 'subject', fallback='Thermod alert'),
                 'credentials': ((euser, epwd) if (euser or epwd) else None)}
        
        global _fake_RPi_Heating, _fake_RPi_Thermometer
        _fake_RPi_Heating = cfg.getboolean('debug', 'fake_rpi_heating', fallback=False)
        _fake_RPi_Thermometer = cfg.getboolean('debug', 'fake_rpi_thermometer', fallback=False)
    
    except configparser.NoSectionError as nse:
        error_code = common.RET_CODE_CFG_FILE_INVALID
        logger.critical('incomplete configuration file, missing `{}` section', nse.section)
    
    except configparser.NoOptionError as noe:
        error_code = common.RET_CODE_CFG_FILE_INVALID
        logger.critical('incomplete configuration file, missing option `{}` '
                        'in section `{}`', noe.option, noe.section)
    
    except configparser.Error as cpe:
        error_code = common.RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('unknown error in configuration file: {}', cpe)
    
    except ValueError as ve:
        # Raised by getboolean(), getfloat(), getint() and int() methods
        # and if heating, switch_on_level or thermometer are not valid.
        error_code = common.RET_CODE_CFG_FILE_INVALID
        logger.critical('invalid configuration: {}', ve)
    
    except OverflowError as oe:
        error_code = common.RET_CODE_CFG_FILE_INVALID
        logger.critical('invalid configuration: {}', oe)
    
    except Exception as e:
        error_code = common.RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('unknown error in configuration file: {}', e)
    
    except KeyboardInterrupt:
        error_code = common.RET_CODE_KEYB_INTERRUPT
    
    except:
        error_code = common.RET_CODE_CFG_FILE_UNKNOWN_ERR
        logger.critical('unknown error in configuration file, no more details')
    
    else:
        error_code = common.RET_CODE_OK
        logger.debug('main settings parsed')
    
    return (Settings(enabled, debug, tt_file, interval, scale, inertia,
                     heating, cooling, thermometer, host, port, email),
            error_code)

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
