# -*- coding: utf-8 -*-
"""Interface to the thermometer.

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
#from json.decoder import JSONDecodeError
from threading import Thread, Event
from collections import deque
from .config import ScriptError, check_script

# backward compatibility for Python 3.4 (TODO check for better handling)
if sys.version[0:3] >= '3.5':
    from json.decoder import JSONDecodeError
else:
    JSONDecodeError = ValueError

__date__ = '2016-02-04'
__updated__ = '2017-01-23'

logger = logging.getLogger(__name__)


def celsius2fahrenheit(value):
    """Convert celsius temperature to fahrenheit degrees."""
    return ((1.8 * value) + 32.0)

def fahrenheit2celsius(value):
    """Convert fahrenheit temperature to celsius degrees."""
    return ((value - 32.0) / 1.8)


class ThermometerError(RuntimeError):
    """Main exception for thermomter-related errors.
    
    The attribute `suberror` can contain additional informations about the
    error. These informations are not printed nor returned by default and
    must be accessed directly.
    """
    
    def __init__(self, error=None, suberror=None):
        super().__init__(error)
        self.suberror = suberror


class ScriptThermometerError(ThermometerError, ScriptError):
    """Like ThermometerError with the name of the script that produced the error.
    
    The script is saved in the attribute ScriptThermometerError.script and must
    be accessed directly, it is never printed by default.
    """
    
    def __init__(self, error=None, suberror=None, script=None):
        super().__init__(error)
        self.suberror = suberror
        self.script = script


class BaseThermometer(object):
    """Basic implementation of a thermometer.
    
    The property `temperature` must be implemented in subclasses and must
    return the current temperature as a float number. Also `release_resources()`
    method must be implemented in subclasses, it is executed during daemon
    shutdown in order to release acquired hardware resources (the default
    implementation does nothing).
    
    During instantiation a degree scale must be specified, in order to
    correctly handle conversion methods: `to_celsius()` and `to_fahrenheit()`.
    """

    DEGREE_CELSIUS = 'C'
    DEGREE_FAHRENHEIT = 'F'
    
    def __init__(self, scale=DEGREE_CELSIUS):
        """Init the thermometer with a choosen degree scale."""
        
        logger.debug('initializing %s with %s degrees',
                     self.__class__.__name__,
                     ((scale == BaseThermometer.DEGREE_CELSIUS)
                        and 'celsius'
                        or 'fahrenheit'))
        
        self._scale = scale
    
    def __repr__(self, *args, **kwargs):
        return '{}.{}({!r})'.format(self.__module__,
                                    self.__class__.__name__,
                                    self._scale)
    
    def __str__(self, *args, **kwargs):
        return '{:.2f} °{}'.format(self.temperature, self._scale)
    
    def __format__(self, format_spec, *args, **kwargs):
        return '{:{}}'.format(self.temperature, format_spec)
    
    @property
    def temperature(self):
        """This method must be implemented in subclasses.
        
        The subclasses methods must return the current temperature as a
        float number in the scale selected during class instantiation in order
        to correctly handle conversion methods and must raise a ThermometerError
        in case of failure.
        
        @exception ThermometerError if an error occurred in retriving temperature
        """
        raise NotImplementedError()
    
    def release_resources(self):
        """This method can be implemented in subclasses.
        
        Should be used to release possibly acquired hardware resources because
        it is executed during daemon shutdown. This default implementation
        does nothing.
        """
        
        pass
    
    def to_celsius(self):
        """Return the current temperature in Celsius degrees."""
        if self._scale == BaseThermometer.DEGREE_CELSIUS:
            return self.temperature
        else:
            return fahrenheit2celsius(self.temperature)
    
    def to_fahrenheit(self):
        """Return the current temperature in Fahrenheit dgrees."""
        if self._scale == BaseThermometer.DEGREE_FAHRENHEIT:
            return self.temperature
        else:
            return celsius2fahrenheit(self.temperature)


class FakeThermometer(BaseThermometer):
    """Fake thermometer that always returns 20.0 degrees celsius or 68.0 fahrenheit."""
    
    @property
    def temperature(self):
        t = 20.0
        if self._scale == BaseThermometer.DEGREE_CELSIUS:
            return t
        else:
            return celsius2fahrenheit(t)


# TODO inserire documentazione su come creare questa board con TMP36 e su
# come viene misurata la temperatura facendo la media di più valori.
class PiAnalogZeroThermometer(BaseThermometer):
    """Read temperature from a Raspberry Pi AnalogZero board in celsius degree.
    
    If a single channel is provided during object creation, it's value is used
    as temperature, if more than one channel is provided, the current
    temperature is computed averaging the values of all channels.
    
    @see http://rasp.io/analogzero/
    """
    
    def __init__(self, channels, multiplier=1, shift=0, scale=BaseThermometer.DEGREE_CELSIUS):
        """Init PiAnalogZeroThermometer object using `channels` of the A/D converter.
        
        @param channels the list of channels to read value from
        @param multiplier the multiplier to calibrate the raw temperature from board
        @param shift the shift value to calibrate the raw temperature from board
        
        @exception ValueError if no channels provided or channels out of range [0,7]
        @exception ThermometerError if the module `gpiozero' cannot be imported
        """
        
        super().__init__(scale)
        
        if len(channels) == 0:
            raise ValueError('missing input channel for PiAnalogZero thermometer')
        
        for c in channels:
            if c > 7:
                raise ValueError('input channels for PiAnalogZero must be in range 0-7, {} given'.format(c))
        
        try:
            logger.debug('importing gpiozero module')
            gpiozero = __import__('gpiozero')
        except ImportError as ie:
            raise ThermometerError('cannot import module `gpiozero`', str(ie))
        
        self._vref = ((3.32/(3.32+7.5))*3.3*1000)
        self._adc = [gpiozero.MCP3008(channel=c) for c in channels]
        
        self._multiplier = float(multiplier)
        self._shift = float(shift)
        
        # Allocate the queue for the last 30 temperatures to be averaged. The
        # value `30` covers a period of 3 minutes because the sleep time between
        # two measures is 6 seconds: 6*30 = 180 seconds = 3 minutes.
        maxlen = 30
        self._temperatures = deque([self.realtime_temperature for t in range(maxlen)], maxlen)
        
        # start averaging thread
        self._stop = Event()
        self._averaging_thread = Thread(target=self._update_temperatures, daemon=True)
        self._averaging_thread.start()
    
    def __repr__(self, *args, **kwargs):
        return '{module}.{cls}({chnnels!r}, {multiplier!r}, {shift!r}, {scale!r})'.format(
                    module=self.__module__,
                    cls=self.__class__.__name__,
                    channels=[adc.channel for adc in self._adc],
                    multiplier=self._multiplier,
                    shift=self._shift,
                    scale=self._scale)
    
    @property
    def realtime_temperature(self):
        """The current temperature as measured by physical thermometer.
        
        If more than one channel is provided during object creation, the
        returned temperature is the average value computed on all channels.
        """
        
        temp = sum([(((adc.value * self._vref) - 500) / 10) for adc in self._adc]) / len(self._adc)
        return ((self._multiplier * temp) + self._shift)
    
    def _update_temperatures(self):
        """Start a cycle to update the list of last measured temperatures.
        
        This method should be run in a separate thread in order to maintain
        the list `self._temperatures` always updated with the last measured
        temperatures.
        """
        
        logger.debug('starting temperature updating cycle')
        
        while not self._stop.wait(6):
            self._temperatures.append(self.realtime_temperature)
    
    @property
    def temperature(self):
        """Return the average of the last measured temperatures.
        
        The average is the way to reduce fluctuation in measurment. Precisely
        the least 5 and the greatest 5 temperatures are excluded, even this
        trick is to stabilize the returned value.
        """
        
        skip = 5
        temp1 = list(self._temperatures)
        temp1.sort()
        temp2 = temp1[skip:(len(temp1)-skip)]
        return sum(temp2) / len(temp2)
    
    def release_resources(self):
        """Stop the temperature-averaging thread."""
        self._stop.set()
        self._averaging_thread.join(6)


class ScriptThermometer(BaseThermometer):
    """Manage the real thermometer through an external script.
    
    The script, provided during initialization, is the interfaces to retrive
    the current temperature from the thermometer. It must be POSIX compliant,
    must exit with code 0 on success and 1 on error and must accept
    (or at least ignore) '--debug' argument that is appended when this class
    is instantiated with `debug==True` (i.e. when Thermod daemon is executed
    in debug mode). In addition, the script must write to the standard output
    a JSON string with the following fields:
    
        - `temperature`: with the current temperature as a number;
        
        - `error`: the error message in case of failure, `null` or empty
          string otherwise.
    """
    
    DEBUG_OPTION = '--debug'
    JSON_TEMPERATURE = 'temperature'
    JSON_ERROR = 'error'
    
    def __init__(self, script, debug=False, scale=BaseThermometer.DEGREE_CELSIUS):
        """Initialiaze a script-based thermometer.
        
        The first parameter must be a string containing the full paths to
        the script with options (like `/usr/local/bin/get-temp -j --opt`) or an
        array with the script to be executed followed by the options
        (like `['/usr/local/bin/get-temp', '-j', '--opt']`).
        
        If the script must be executed with '--debug' option appended, set the
        `debug` parameter to `True`.
        
        @exception ScriptError if the provided script cannot be found or executed
        """
        
        super().__init__(scale)
        
        if isinstance(script, list):
            self._script = deepcopy(script)
        elif isinstance(script, str):
            self._script = shlex.split(script, comments=True)
        else:
            raise TypeError('the script parameter must be string or list')
        
        if debug:
            self._script.append(ScriptThermometer.DEBUG_OPTION)
        
        check_script(self._script[0])
        
        logger.debug('%s initialized with script: `%s`',
                     self.__class__.__name__,
                     self._script)
    
    def __repr__(self, *args, **kwargs):
        return '{module}.{cls}({script!r}, {debug!r}, {scale!r})'.format(
                    module=self.__module__,
                    cls=self.__class__.__name__,
                    script=self._script,
                    debug=(ScriptThermometer.DEBUG_OPTION in self._script),
                    scale=self._scale)
    
    @property
    def temperature(self):
        """Retrive the current temperature executing the script.
        
        The return value is a float number. Many exceptions can be raised
        if the script cannot be executed or if the script exit with errors.
        """
        logger.debug('retriving current temperature')
        
        try:
            raw = subprocess.check_output(self._script, shell=False)
            out = json.loads(raw.decode('utf-8'))
            
            tstr = out[ScriptThermometer.JSON_TEMPERATURE]
            t = float(tstr)
        
        except subprocess.CalledProcessError as cpe:  # error in subprocess
            suberr = 'the temperature script exited with return code {}'.format(cpe.returncode)
            logger.debug(suberr)
            
            try:
                out = json.loads(cpe.output.decode('utf-8'))
            except:
                out = {ScriptThermometer.JSON_ERROR: '{} and the output is invalid'.format(suberr)}
            
            err = None
            if ScriptThermometer.JSON_ERROR in out:
                err = out[ScriptThermometer.JSON_ERROR]
                logger.debug(err)
            
            raise ScriptThermometerError((err or suberr), suberr, self._script[0])
        
        except FileNotFoundError as fnfe:
            raise ScriptThermometerError('cannot find script', str(fnfe), self._script[0])
        
        except PermissionError as pe:
            raise ScriptThermometerError('cannot execute script', str(pe), self._script[0])
        
        except JSONDecodeError as jde:  # error in json.loads()
            logger.debug('the script output is not in JSON format')
            raise ScriptThermometerError('script output is invalid, cannot get '
                                         'current temperature', str(jde),
                                         self._script[0])
        
        except KeyError as ke:  # error in retriving element from out dict
            logger.debug('the output of temperature script lacks the `%s` item',
                         ScriptThermometer.JSON_TEMPERATURE)
            
            raise ScriptThermometerError('the temperature script has not '
                                         'returned the current temperature',
                                         str(ke), self._script[0])
            
        except (ValueError, TypeError) as vte:  # error converting to float
            logger.debug('cannot convert temperature `%s` to number', tstr)
            raise ScriptThermometerError('the temperature script returned an '
                                         'invalid value', str(vte),
                                         self._script[0])
        
        logger.debug('current temperature: %.2f', t)
        return t

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab