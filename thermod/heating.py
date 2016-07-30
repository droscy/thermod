# -*- coding: utf-8 -*-
"""Interface to the real heating."""

import sys
import json
import shlex
import logging
import subprocess
from copy import deepcopy
from datetime import datetime
#from json.decoder import JSONDecodeError
from .config import ScriptError

# backward compatibility for Python 3.4 (TODO check for better handling)
if sys.version[0:3] >= '3.5':
    from json.decoder import JSONDecodeError
else:
    JSONDecodeError = ValueError

__date__ = '2015-12-30'
__updated__ = '2016-06-29'

logger = logging.getLogger(__name__)


class HeatingError(RuntimeError):
    """Main exception for heating-related errors.
    
    The attribute `suberror` can contain additional informations about the
    error. These informations are not printed nor returned by default and
    must be accessed directly.
    """
    
    def __init__(self, error=None, suberror=None):
        super().__init__(error)
        self.suberror = suberror


class ScriptHeatingError(HeatingError, ScriptError):
    """Like HeatingError with the name of the script that produced the error.
    
    The script is saved in the attribute ScriptHeatingError.script and must
    be accessed directly, it is never printed by default.
    """
    
    def __init__(self, error=None, suberror=None, script=None):
        super().__init__(error)
        self.suberror = suberror
        self.script = script


class BaseHeating(object):
    """Basic implementation to simulate a real heating.
    
    Every method should be reimplemented in subclasses to interface with the
    real heating hardware.
    """
    
    def __init__(self):
        self._is_on = False
        """If the heating is currently on."""
        
        self._switch_off_time = datetime.fromtimestamp(0)
        """Time of last switch off."""
    
    def __repr__(self, *args, **kwargs):
        return '{}.{}()'.format(self.__module__, self.__class__.__name__)
    
    def __str__(self, *args, **kwargs):
        return (self._is_on and 'ON' or 'OFF')
    
    def __format__(self, format_spec, *args, **kwargs):
        return '{:{}}'.format(str(self), format_spec)
    
    def switch_on(self):
        """Switch on the heating, raise a `HeatingError` in case of failure.
        
        Subclasses that reimplement this method should adhere to this beahviour
        and raise a `HeatingError` in case of failure
        """
        
        self._is_on = True
    
    def switch_off(self):
        """Switch off the heating, raise a `HeatingError` in case of failure.
        
        Subclasses that reimplement this method should adhere to this beahviour
        and raise a `HeatingError` in case of failure
        """
        
        self._is_on = False
        self._switch_off_time = datetime.now()
    
    def status(self):
        """Return the status of the heating as an integer: 1=ON, 0=OFF.
        
        Subclasses that reimplement this method should return an integer
        value to be fully compatible.
        """
        
        return int(self._is_on)
    
    def is_on(self):
        """Return `True` if the heating is currently on, `False` otherwise.
        
        Subclasses that reimplement this method should return a boolean
        value to be fully compatible.
        """
        
        return self._is_on
    
    def switch_off_time(self):
        """Return the last time the heating has been switched off.
        
        Subclasses that reimplement this method should return a `datetime`
        object to be fully compatible.
        """
        
        return self._switch_off_time


class ScriptHeating(BaseHeating):
    """Manage the real heating through three external scripts.
    
    The three scripts, provided during initialization, are the interfaces to
    the hardware of the heating: one to switch on the heating, one to switch it
    off and the last one to retrive the current status.
    
    The three scripts must be POSIX compliant, must exit with code 0 on success
    and 1 on error and must accept (or at least ignore) '--debug' argument that
    is appended when this class is instantiated with `debug==True` (i.e. when
    Thermod daemon is executed in debug mode). In addition they must write to
    the standard output a JSON string with the following fields:
    
        - `success`: if the operation has been completed successfully or not
          (boolean value `true` for success and `false` for failure);
        
        - `status`: the current status of the heating (as integer: 1=ON, 0=OFF,
          or `null` if an error occurred);
        
        - `error`: the error message in case of failure, `null` or empty
          string otherwise.
    """
    DEBUG_OPTION = '--debug'
    JSON_SUCCESS = 'success'
    JSON_STATUS = 'status'
    JSON_ERROR = 'error'
    
    def __init__(self, switchon, switchoff, status, debug=False):
        """Init the `ScriptHeating` object.
        
        The first three parameters must be strings containing the full paths to
        the scripts with options (like `/usr/local/bin/switchoff -j -v`) or an
        array with the script to be executed followed by the options
        (like `['/usr/local/bin/switchoff', '-j', '-v']`).
        
        If the scripts must be executed with '--debug' option appended, set the
        `debug` parameter to `True`.
        """
        
        logger.debug('initializing {}'.format(self.__class__.__name__))
        
        self._is_on = None
        """The last status of the heating.
        
        The pourpose of this attribute is to avoid too many hardware requests
        to the heating. Whenever `switch_on()`, `switch_off()` or `status()`
        methods are executed this value changes to reflect the new current
        status, while the `is_on()` method simply returns this value.
        """
        
        self._switch_off_time = datetime.fromtimestamp(0)
        """The last time the heating has been switched off."""
        
        if isinstance(switchon, list):
            self._switch_on_script = deepcopy(switchon)
        elif isinstance(switchon, str):
            self._switch_on_script = shlex.split(switchon, comments=True)
        else:
            raise TypeError('the switchon parameter must be string or list')
        
        if isinstance(switchoff, list):
            self._switch_off_script = deepcopy(switchoff)
        elif isinstance(switchoff, str):
            self._switch_off_script = shlex.split(switchoff, comments=True)
        else:
            raise TypeError('the switchoff parameter must be string or list')
        
        if isinstance(status, list):
            self._status_script = deepcopy(status)
        elif isinstance(status, str):
            self._status_script = shlex.split(status, comments=True)
        else:
            raise TypeError('the status parameter must be string or list')
        
        if debug:
            self._switch_on_script.append(ScriptHeating.DEBUG_OPTION)
            self._switch_off_script.append(ScriptHeating.DEBUG_OPTION)
            self._status_script.append(ScriptHeating.DEBUG_OPTION)
        
        logger.debug('{} initialized with scripts ON=`{}`, OFF=`{}` and JSON_STATUS=`{}`'
                     .format(self.__class__.__name__,
                             self._switch_on_script[0],
                             self._switch_off_script[0],
                             self._status_script[0]))
    
    def __repr__(self, *args, **kwargs):
        return '{module}.{cls}({on!r}, {off!r}, {status!r}, {debug!r})'.format(
                    module=self.__module__,
                    cls=self.__class__.__name__,
                    on=self._switch_on_script,
                    off=self._switch_off_script,
                    status=self._status_script,
                    debug=(ScriptHeating.DEBUG_OPTION in self._status_script))
    
    def switch_on(self):
        """Switch on the heating executing the `switch-on` script."""
        
        logger.debug('switching on the heating')
        
        try:
            subprocess.check_output(self._switch_on_script, shell=False)
        
        except subprocess.CalledProcessError as cpe:
            suberr = 'the switch-on script exited with return code `{}`'.format(cpe.returncode)
            logger.debug(suberr)
            
            try:
                out = json.loads(cpe.output.decode('utf-8'))
            except:
                out = {ScriptHeating.JSON_ERROR: '{} and the output is invalid'.format(suberr)}
            
            err = None
            if ScriptHeating.JSON_ERROR in out:
                err = out[ScriptHeating.JSON_ERROR]
                logger.debug('switch-on: {}'.format(err))
            
            raise ScriptHeatingError((err or suberr), suberr, self._switch_on_script[0])
        
        self._is_on = True
        logger.debug('heating switched on')
    
    def switch_off(self):
        """Switch off the heating executing the `switch-off` script."""
        
        logger.debug('switching off the heating')
        
        try:
            subprocess.check_output(self._switch_off_script, shell=False)
        
        except subprocess.CalledProcessError as cpe:
            suberr = 'the switch-off script exited with return code {}'.format(cpe.returncode)
            logger.debug(suberr)
            
            try:
                out = json.loads(cpe.output.decode('utf-8'))
            except:
                out = {ScriptHeating.JSON_ERROR: '{} and the output is invalid'.format(suberr)}
            
            err = None
            if ScriptHeating.JSON_ERROR in out:
                err = out[ScriptHeating.JSON_ERROR]
                logger.debug('switch-off: {}'.format(err))
            
            raise ScriptHeatingError((err or suberr), suberr, self._switch_off_script[0])
        
        self._is_on = False
        self._switch_off_time = datetime.now()
        logger.debug('heating switched off at {}'.format(self._switch_off_time))
    
    def status(self):
        """Execute the `status` script and return the current status of the heating.
        
        The returned value is an integer: 1 for ON and 0 for OFF.
        """
        
        logger.debug('retriving current status of the heating')
        
        try:
            raw = subprocess.check_output(self._status_script, shell=False)
            out = json.loads(raw.decode('utf-8'))
            
            ststr = out[ScriptHeating.JSON_STATUS]
            status = int(ststr)
        
        except subprocess.CalledProcessError as cpe:  # error in subprocess
            suberr = 'the status script exited with return code {}'.format(cpe.returncode)
            logger.debug(suberr)
            
            try:
                out = json.loads(cpe.output.decode('utf-8'))
            except:
                out = {ScriptHeating.JSON_ERROR: '{} and the output is invalid'.format(suberr)}
            
            err = None
            if ScriptHeating.JSON_ERROR in out:
                err = out[ScriptHeating.JSON_ERROR]
                logger.debug('status: {}'.format(err))
            
            raise ScriptHeatingError((err or suberr), suberr, self._status_script[0])
        
        except JSONDecodeError as jde:  # error in json.loads()
            logger.debug('the script output is not in JSON format')
            raise ScriptHeatingError('script output is invalid, cannot get '
                                     'current status', str(jde),
                                     self._status_script[0])
        
        except KeyError as ke:  # error in retriving element from output dict
            logger.debug('the script output lacks the `{}` item'
                         .format(ScriptHeating.JSON_STATUS))
            
            raise ScriptHeatingError('the status script has not returned the '
                                     'current heating status', str(ke),
                                     self._status_script[0])
            
        except (ValueError, TypeError) as vte:  # error converting to int
            logger.debug('cannot convert status `{}` to integer'.format(ststr))
            raise ScriptHeatingError('the status script returned an invalid '
                                     'status', str(vte), self._status_script[0])
            
        logger.debug('the heating is currently {}'.format((status and 'ON' or 'OFF')))
        logger.debug('last switch off time: {}'.format(self._switch_off_time))
        
        self._is_on = bool(status)
        return status
    
    def is_on(self):
        """Return `True` if the heating is ON, `False` otherwise.
        
        Usually, this method, does not execute any script (except on first
        invocation) and simply returns the last seen status. External
        classes/applications can call this method frequently without producing
        performance issues on the machine. The first invocation is likely
        to execute the status() method if no status has ever been read from
        the hardware.
        
        To retrive the real current status as reported by the hardware
        consider executing the `status()` method.
        """
        
        if self._is_on is None:
            self.status()
        
        return self._is_on
    
    def switch_off_time(self):
        """Return the last time the heating has been switched off."""
        return self._switch_off_time


# only for debug purpose
if __name__ == '__main__':
    heating = ScriptHeating('python3 scripts/switch.py --on -j',
                            'python3 scripts/switch.py --off -j',
                            'python3 scripts/switch.py --status -j')
    
    print('JSON_STATUS: {}'.format(heating.status() and 'ON' or 'OFF'))
    print('IS ON: {}'.format(heating.is_on() and 'ON' or 'OFF'))
    
    heating.switch_off()
    print('JSON_STATUS: {}'.format(heating.status() and 'ON' or 'OFF'))
    print('IS ON: {}'.format(heating.is_on() and 'ON' or 'OFF'))
    
    heating.switch_on()
    print('JSON_STATUS: {}'.format(heating.status() and 'ON' or 'OFF'))
    print('IS ON: {}'.format(heating.is_on() and 'ON' or 'OFF'))
    
    heating.switch_on()
    print('JSON_STATUS: {}'.format(heating.status() and 'ON' or 'OFF'))
    print('IS ON: {}'.format(heating.is_on() and 'ON' or 'OFF'))

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab