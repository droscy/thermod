# -*- coding: utf-8 -*-
"""Common classes and constants for thermod package and Thermod daemon.

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

import sys
import logging
from datetime import datetime
from collections import namedtuple

__date__ = '2017-03-02'
__updated__ = '2018-06-21'


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
RET_CODE_CFG_FILE_MISSING = 10
RET_CODE_CFG_FILE_SYNTAX_ERR = 11
RET_CODE_CFG_FILE_INVALID = 12
RET_CODE_CFG_FILE_UNKNOWN_ERR = 13
RET_CODE_TT_NOT_FOUND = 20
RET_CODE_TT_READ_ERR = 21
RET_CODE_TT_INVALID_SYNTAX = 22
RET_CODE_TT_INVALID_CONTENT = 23
RET_CODE_OS_INIT_ERR = 24
RET_CODE_HW_INIT_ERR = 25
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

TIMESTAMP_MAX_VALUE = _tmv
"""Max value for a POSIX timestamp in runnin platform."""


ThermodStatus = namedtuple('ThermodStatus',
                           ['timestamp', 'status', 'heating_status',
                            'current_temperature', 'target_temperature',
                            'error', 'explain'])
"""Contain current global status of the thermostat.

 * `timestamp` is the current time in seconds since the epoch
 * `status` is the status of the thermostat (see `timetable.JSON_ALL_STATUSES`)
 * `heating_status` is the status of the heating (it's an int: 1=ON, 0=OFF)
 * `current_temperature` is the current temperature in the choosen degree scale
 * `target_temperature` is the temperature to be reached
 * `error` if an error occurred this is the error (`None` if no error)
 * `explain` a longer description of the error, if available
"""

# Set default values for ThermodStatus and ThermodError tuples (timestamp is
# always required, thus the '-1' in len function below).
ThermodStatus.__new__.__defaults__ = (None,) * (len(ThermodStatus._fields) - 1)


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
    
    @property
    def level(self):
        return self.logger.level
    
    def setLevel(self, level):
        self.logger.setLevel(level)


class ScriptError(RuntimeError):
    """Handle error of an external script.
    
    Can be used in conjuction with other exceptions to store also the name
    of the external script that produced the error. This script name is never
    returned by default methods, it must be requested manually.
    """
    
    def __init__(self, error=None, script=None):
        super().__init__(error)
        self.script = script

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab