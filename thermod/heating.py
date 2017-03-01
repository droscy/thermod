# -*- coding: utf-8 -*-
"""Interface to the real heating.

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

import sys
import json
import shlex
import logging
import subprocess

from copy import deepcopy
from datetime import datetime
#from json.decoder import JSONDecodeError
from .config import ScriptError, check_script, LogStyleAdapter

# backward compatibility for Python 3.4 (TODO check for better handling)
if sys.version[0:3] >= '3.5':
    from json.decoder import JSONDecodeError
else:
    JSONDecodeError = ValueError

__date__ = '2015-12-30'
__updated__ = '2017-02-28'

logger = LogStyleAdapter(logging.getLogger(__name__))


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
        logger.debug('initializing {}', self.__class__.__name__)
        
        self._is_on = False
        """If the heating is currently on."""
        
        self._switch_off_time = datetime.fromtimestamp(0)
        """The last time the heating has been switched off."""
    
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
    
    @property
    def status(self):
        """Return the status of the heating as an integer: 1=ON, 0=OFF.
        
        Subclasses that reimplement this method should return an integer
        value to be fully compatible.
        """
        
        return int(self.is_on())
    
    def is_on(self):
        """Return `True` if the heating is currently on, `False` otherwise.
        
        Subclasses that reimplement this method should return a boolean
        value to be fully compatible.
        """
        
        return self._is_on
    
    @property
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
        
        @exception ScriptError if any of the provided scripts cannot be found or executed
        """
        
        super().__init__()
        
        self._is_on = None
        """The last status of the heating.
        
        The pourpose of this attribute is to avoid too many hardware requests
        to the heating. Whenever `switch_on()`, `switch_off()` or
        `force_status_update()` methods are executed this value changes to
        reflect the new current status, while the `is_on()` and `status()`
        method simply returns this value.
        """
        
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
            logger.debug('appending {} to scripts command', ScriptHeating.DEBUG_OPTION)
            self._switch_on_script.append(ScriptHeating.DEBUG_OPTION)
            self._switch_off_script.append(ScriptHeating.DEBUG_OPTION)
            self._status_script.append(ScriptHeating.DEBUG_OPTION)
        
        logger.debug('checking executability of provided scripts')
        check_script(self._switch_on_script[0])
        check_script(self._switch_off_script[0])
        check_script(self._status_script[0])
        
        logger.debug('{} initialized with scripts ON=`{}`, OFF=`{}` and STATUS=`{}`',
                     self.__class__.__name__,
                     self._switch_on_script[0],
                     self._switch_off_script[0],
                     self._status_script[0])
    
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
                logger.debug('switch-on: {}', err)
            
            raise ScriptHeatingError((err or suberr), suberr, self._switch_on_script[0])
        
        except FileNotFoundError as fnfe:
            raise ScriptHeatingError('cannot find script', str(fnfe), self._switch_on_script[0])
        
        except PermissionError as pe:
            raise ScriptHeatingError('cannot execute script', str(pe), self._switch_on_script[0])
        
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
                logger.debug('switch-off: {}', err)
            
            raise ScriptHeatingError((err or suberr), suberr, self._switch_off_script[0])
        
        except FileNotFoundError as fnfe:
            raise ScriptHeatingError('cannot find script', str(fnfe), self._switch_off_script[0])
        
        except PermissionError as pe:
            raise ScriptHeatingError('cannot execute script', str(pe), self._switch_off_script[0])
        
        self._is_on = False
        self._switch_off_time = datetime.now()
        logger.debug('heating switched off at {}', self._switch_off_time)
    
    def force_status_update(self):
        """Execute the `status` script and update internal status."""
        
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
                logger.debug('status: {}', err)
            
            raise ScriptHeatingError((err or suberr), suberr, self._status_script[0])
        
        except FileNotFoundError as fnfe:
            raise ScriptHeatingError('cannot find script', str(fnfe), self._status_script[0])
        
        except PermissionError as pe:
            raise ScriptHeatingError('cannot execute script', str(pe), self._status_script[0])
        
        except JSONDecodeError as jde:  # error in json.loads()
            logger.debug('the script output is not in JSON format')
            raise ScriptHeatingError('script output is invalid, cannot get '
                                     'current status', str(jde),
                                     self._status_script[0])
        
        except KeyError as ke:  # error in retriving element from output dict
            logger.debug('the script output lacks the `{}` item',
                         ScriptHeating.JSON_STATUS)
            
            raise ScriptHeatingError('the status script has not returned the '
                                     'current heating status', str(ke),
                                     self._status_script[0])
            
        except (ValueError, TypeError) as vte:  # error converting to int
            logger.debug('cannot convert status `{}` to integer', ststr)
            raise ScriptHeatingError('the status script returned an invalid '
                                     'status', str(vte), self._status_script[0])
            
        logger.debug('the heating is currently {}', (status and 'ON' or 'OFF'))
        logger.debug('last switch off time: {}', self._switch_off_time)
        
        self._is_on = bool(status)
    
    def is_on(self):
        """Return `True` if the heating is ON, `False` otherwise.
        
        Usually, this method, does not execute any script (except on first
        invocation) and simply returns the last seen status. External
        classes/applications can call this method frequently without producing
        performance issues on the machine. The first invocation is likely
        to execute the `force_status_update()` method if no status has ever
        been read from the hardware.
        
        To retrive the real current status as reported by the hardware
        consider executing the `force_status_update()` method.
        """
        
        if self._is_on is None:
            self.force_status_update()
        
        return self._is_on


try:
    # Try importing RPi.GPIO module, if succeded spcific classes for
    # Raspberry Pi are defined, otherwise fake classes are created in the
    # `except` section below.
    
    # IMPORTANT: for any new classes defined here, a fake one must be defined in except section!
    
    logger.debug('importing RPi.GPIO module')
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    
    class PiPinsRelayHeating(BaseHeating):
        """Use relays connected to GPIO pins to switch on/off the heating."""
        
        def __init__(self, pins, switch_on_level):
            """Init GPIO `pins` connected to relays.
            
            @param pins single pin or list of BCM GPIO pins to use
            @param switch_on_level GPIO trigger level to swith on the heating,
                can be `RPi.GPIO.HIGH` or 'h' for high level trigger,
                `RPi.GPIO.LOW` or 'l' for low level trigger.
            
            @exception ValueError if no pins provided or pin number out of
                range [0,27] or switch on level is invalid.
            @exception HeatingError if the module `RPi.GPIO' cannot be loaded.
            """
            
            super().__init__()
            
            # Private reference to GPIO.cleanup() method, required to be used
            # in the __del__() method below.
            self.cleanup = GPIO.cleanup
            
            try:
                self._pins = [int(p) for p in pins]
            except TypeError:
                # only a single pin is provided
                self._pins = [int(pins)]
            
            if len(self._pins) == 0:
                raise ValueError('no pins provided')
            
            for p in self._pins:
                if p not in range(28):
                    raise ValueError('pin number must be in range 0-27, {} given'.format(p))
            
            if switch_on_level in (GPIO.HIGH, 'h'):
                logger.debug('setting HIGH level to switch on the heating')
                self._on = GPIO.HIGH
                self._off = GPIO.LOW
            elif switch_on_level in (GPIO.LOW, 'l'):
                logger.debug('setting LOW level to switch on the heating')
                self._on = GPIO.LOW
                self._off = GPIO.HIGH
            else:
                raise ValueError('switch on level `{}` is not valid'.format(switch_on_level))
            
            logger.debug('initializing GPIO pins {}', self._pins)
            GPIO.setup(self._pins, GPIO.OUT)
            GPIO.output(self._pins, self._off)
        
        def __repr__(self, *args, **kwargs):
            return '{module}.{cls}({pins!r}, {level!r})'.format(
                        module=self.__module__,
                        cls=self.__class__.__name__,
                        pins=self._pins,
                        level=self._on)
        
        def switch_on(self):
            """Switch on the heating setting right level to GPIO pins."""
            logger.debug('switching on the heating setting level {} to pins {}', self._on, self._pins)
            GPIO.output(self._pins, self._on)
        
        def switch_off(self):
            """Switch off the heating setting right level to GPIO pins."""
            logger.debug('switching off the heating setting level {} to pins {}', self._off, self._pins)
            GPIO.output(self._pins, self._off)
            self._switch_off_time = datetime.now()
            logger.debug('heating switched off at {}', self._switch_off_time)
        
        def is_on(self):
            """Return `True` if the heating is currently on, `False` otherwise.
            
            Actually returns `True` if the first used pin has a level equal
            to `self._on` value. Other pins, if used, are ignored.
            """
            
            return (GPIO.input(self._pins[0]) == self._on)
        
        def __del__(self):
            """Cleanup used GPIO pins."""
            # cannot use logger here, the logger could be already unloaded
            self.cleanup(self._pins)

except ImportError as ie:
    # The running system is not a Raspberry Pi or the RPi.GPIO module is not
    # installed, in both case fake Pi* classes are defined. If an object of the
    # following classes is created, an exception is raised.
    
    logger.debug('module RPi.GPIO not found, probably the running system is not a Raspberry Pi')
    
    # fake classes
    class PiPinsRelayHeating(BaseHeating):
        def __init__(self, *args, **kwargs):
            raise HeatingError('module RPi.GPIO not loaded')


# only for debug purpose
if __name__ == '__main__':
    heating = ScriptHeating('python3 scripts/switch.py --on -j',
                            'python3 scripts/switch.py --off -j',
                            'python3 scripts/switch.py --status -j')
    
    print('STATUS: {}'.format(heating.status() and 'ON' or 'OFF'))
    print('IS ON: {}'.format(heating.is_on() and 'ON' or 'OFF'))
    
    heating.switch_off()
    print('STATUS: {}'.format(heating.status() and 'ON' or 'OFF'))
    print('IS ON: {}'.format(heating.is_on() and 'ON' or 'OFF'))
    
    heating.switch_on()
    print('STATUS: {}'.format(heating.status() and 'ON' or 'OFF'))
    print('IS ON: {}'.format(heating.is_on() and 'ON' or 'OFF'))
    
    heating.switch_on()
    print('STATUS: {}'.format(heating.status() and 'ON' or 'OFF'))
    print('IS ON: {}'.format(heating.is_on() and 'ON' or 'OFF'))

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab