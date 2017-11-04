# -*- coding: utf-8 -*-
"""Constants and functions about main configuration file.

This module is only useful in main Thermod daemon because it doesn't raise any
exception and uses logger to print info and error messages. 

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
import logging
import configparser
from collections import namedtuple

from . import common

__date__ = '2015-09-13'
__updated__ = '2017-11-03'

logger = common.LogStyleAdapter(logging.getLogger(__name__))


# Main config filename, search paths, classes and parsers
MAIN_CONFIG_FILENAME = 'thermod.conf'
MAIN_CONFIG_FILES = (MAIN_CONFIG_FILENAME,
                     os.path.join(os.path.expanduser('~/.thermod'), MAIN_CONFIG_FILENAME),
                     os.path.join('/usr/local/etc/thermod', MAIN_CONFIG_FILENAME),
                     os.path.join('/etc/thermod', MAIN_CONFIG_FILENAME))


Settings = namedtuple('Settings', ['enabled', 'debug', 'tt_file', 'interval',
                                   'heating', 'thermometer', 'host', 'port',
                                   'email', 'error_code'])
"""Tuple used to transfer settings from config file to main daemon."""


def read_config_file(config_files=None):
    """Search and read main configuration file.
    
    @params config_files a list of possible path for configuration file
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
    
    @params cfg configparser.ConfigParser object to parse data from
    
    @return `thermod.utils.Settings` tuple with the main settings and an error
        code that can be used as POSIX return value (if no error occurred the
        error code is 0)
    
    @exception TypeError if cfg is not a configparser.ConfigParser object
    """
    
    if not isinstance(cfg, configparser.ConfigParser):
        raise TypeError('ConfigParser object is required to parse main settings')
    
    try:
        logger.debug('parsing main settings')
        enabled = cfg.getboolean('global', 'enabled')
        debug = cfg.getboolean('global', 'debug')
        tt_file = cfg.get('global', 'timetable')
        interval = cfg.getint('global', 'interval')
        
        logger.debug('parsing heating settings')
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
        
        logger.debug('parsing thermometer settings')
        _t_ref = cfg.get('thermometer', 't_ref')
        _t_raw = cfg.get('thermometer', 't_raw')
        thermometer = {'script': cfg.get('thermometer', 'thermometer'),
                       't_ref': [float(t) for t in _t_ref.split(',')] if _t_ref else [],
                       't_raw': [float(t) for t in _t_raw.split(',')] if _t_raw else []}
        
        _scale = cfg.get('thermometer', 'scale', fallback='celsius').casefold()
        if _scale not in ('celsius', 'fahrenheit'):
                raise ValueError('the degree scale must be `celsius` or '
                                 '`fahrenheit`, `{}` provided'.format(_scale))
        
        thermometer['scale'] = _scale[0]  # only the first letter of _level is used
        
        if thermometer['script'][0] == '/':
            # If the first char is a / it denotes the beginning of a filesystem
            # path, so the value is acceptable and no additional parameters
            # are required.
            pass
        
        elif thermometer['script'] == 'PiAnalogZero':
            # The user choose to use the internal class for Raspberry Pi
            # thermometer instead of an external script.
            thermometer['channels'] = [int(c) for c in cfg.get('thermometer/PiAnalogZero', 'channels', fallback='').split(',')]
            thermometer['stddev'] = cfg.getfloat('thermometer/PiAnalogZero', 'stddev', fallback=2.0)
        
        # An `elif` can be added with additional specific thermometer classes
        # once they will be created.
        else:
            raise ValueError('invalid value `{}` for thermometer'.format(thermometer['script']))
        
        logger.debug('parsing socket settings')
        host = cfg.get('socket', 'host', fallback=common.SOCKET_DEFAULT_HOST)
        port = cfg.getint('socket', 'port', fallback=common.SOCKET_DEFAULT_PORT)
            
        if (port < 0) or (port > 65535):
            # checking port here because the ControlThread is created after starting
            # the daemon and the resulting log file can be messy
            raise OverflowError('socket port {:d} is outside range 0-65535'.format(port))
        
        logger.debug('parsing email settings')
        eserver = cfg.get('email', 'server').split(':')
        euser = cfg.get('email', 'user', fallback='')
        epwd = cfg.get('email', 'password', fallback='')
        email = {'server': (len(eserver)>1 and (eserver[0], eserver[1]) or eserver[0]),
                 'sender': cfg.get('email', 'sender'),
                 'recipients': [rcpt for _,rcpt in cfg.items('email/rcpt')],
                 'subject': cfg.get('email', 'subject', fallback='Thermod alert'),
                 'credentials': ((euser or epwd) and (euser, epwd) or None)}
    
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
    
    return Settings(enabled, debug, tt_file, interval, heating, thermometer, host, port, email, error_code)


# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
