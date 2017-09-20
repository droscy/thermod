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

import json
import shlex
import logging
import subprocess
import numpy

from copy import deepcopy
from json.decoder import JSONDecodeError
from threading import Thread, Event
from collections import deque

from .utils import check_script
from .common import ScriptError, LogStyleAdapter

try:
    # Try importing spidev or gpiozero module.
    # If succeded spcific classes for  Raspberry Pi are defined, otherwise
    # fake classes are created at the end of this file.
    from spidev import SpiDev
except ImportError:
    SpiDev = False
    try:
        from gpiozero import MCP3008
    except ImportError:
        MCP3008 = False

__date__ = '2016-02-04'
__updated__ = '2017-09-20'

logger = LogStyleAdapter(logging.getLogger(__name__))


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
    """Like `ThermometerError` with the name of the script that produced the error.
    
    The script is saved in the attribute `ScriptThermometerError.script` and
    must be accessed directly, it is never printed by default.
    """
    
    def __init__(self, error=None, suberror=None, script=None):
        super().__init__(error)
        self.suberror = suberror
        self.script = script


class BaseThermometer(object):
    """Basic implementation of a thermometer.
    
    The property `raw_temperature` must be implemented in subclasses and must
    return the current temperature (without calibration) as a float number.
    
    During instantiation a degree scale must be specified, in order to
    correctly handle conversion methods: `to_celsius()` and `to_fahrenheit()`.
    
    The thermometer can be calibrated passing two list of temperatures:
    `t_ref` with reference temperatures and `t_raw` with the corresponding
    values read by the thermometer. These two lists will be used to compute a
    transformation function to calibrate the thermometer. The two lists must
    have the same number of elements and must have at least 6 elements each.
    To disable the calibration or to get the values for `t_raw` list, leave
    `t_raw` itself empty.
    """

    DEGREE_CELSIUS = 'c'
    DEGREE_FAHRENHEIT = 'f'
    
    def __init__(self, scale=DEGREE_CELSIUS, t_ref=[], t_raw=[], calibration=None):
        """Init the thermometer with a choosen degree scale.
        
        @param scale degree scale to be used
        @param t_ref list of reference values for temperature calibration
        @param t_raw list of raw temperatures read by the thermometer
            corresponding to values in `t_ref`
        @param calibration e callable object to calibrate the temperature (if
            both `t_ref` and `t_raw` are valid, this parameter is ignored)
        """
        
        logger.debug('initializing {} with {} degrees',
                     self.__class__.__name__,
                     ('celsius' if scale == BaseThermometer.DEGREE_CELSIUS else 'fahrenheit'))
        
        self._scale = scale
        self._calibrate = numpy.poly1d([1, 0])  # polynomial identity
        
        if len(t_raw) >= 6:
            if len(t_ref) == len(t_raw):
                logger.debug('performing thermometer calibration with t_ref={} and t_raw={}', t_ref, t_raw)
                z = numpy.polyfit(t_raw, t_ref, 5)
                self._calibrate = numpy.poly1d(z)
                logger.debug('calibration completed')
            else:
                raise ThermometerError('cannot perform thermometer calibration '
                                       'because t_ref and t_raw have different '
                                       'number of elements')
        elif calibration is not None:
            logger.debug('using external function to calibrate raw temperature')
            self._calibrate = calibration
        else:
            logger.debug('calibration disabled due to t_raw list empty or too small')
    
    def __repr__(self, *args, **kwargs):
        return '<{}.{}({!r}, calibration={!r})>'.format(self.__module__,
                                                        self.__class__.__name__,
                                                        self._scale,
                                                        self._calibrate)
    
    def __str__(self, *args, **kwargs):
        return '{:.2f} °{}'.format(self.temperature, self._scale)
    
    def __format__(self, format_spec, *args, **kwargs):
        return '{:{}}'.format(self.temperature, format_spec)
    
    @property
    def raw_temperature(self):
        """This method must be implemented in subclasses.
        
        The subclasses' methods must return the current temperature read from
        the thermometer as a float number in the scale selected during class
        instantiation in order to correctly handle conversion methods and must
        raise `ThermometerError` in case of failure.
        
        No calibration adjustment must be performed in this method.
        
        @exception ThermometerError if an error occurred in retriving temperature
        """
        
        raise NotImplementedError()
    
    @property
    def temperature(self):
        """The calibrated temperature."""
        return round(self._calibrate(self.raw_temperature), 2)  # additional decimal are meaningless
    
    def to_celsius(self):
        """Return the current temperature in Celsius degrees."""
        if self._scale == BaseThermometer.DEGREE_CELSIUS:
            return self.temperature
        else:
            return round(fahrenheit2celsius(self.temperature), 2)  # additional decimal are meaningless
    
    def to_fahrenheit(self):
        """Return the current temperature in Fahrenheit dgrees."""
        if self._scale == BaseThermometer.DEGREE_FAHRENHEIT:
            return self.temperature
        else:
            return round(celsius2fahrenheit(self.temperature), 2)  # additional decimal are meaningless


class FakeThermometer(BaseThermometer):
    """Fake thermometer that always returns 20.0 degrees celsius or 68.0 fahrenheit."""
    
    def __init__(self, scale=BaseThermometer.DEGREE_CELSIUS):
        super().__init__(scale)
    
    @property
    def raw_temperature(self):
        t = 20.0
        if self._scale == BaseThermometer.DEGREE_CELSIUS:
            return t
        else:
            return round(celsius2fahrenheit(t), 2)


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
    
    def __init__(self, script, debug=False, scale=BaseThermometer.DEGREE_CELSIUS, t_ref=[], t_raw=[], calibration=None):
        """Initialiaze a script-based thermometer.
        
        The first parameter must be a string containing the full paths to
        the script with options (like `/usr/local/bin/get-temp -j --opt`) or an
        array with the script to be executed followed by the options
        (like `['/usr/local/bin/get-temp', '-j', '--opt']`).
        
        If the script must be executed with '--debug' option appended, set the
        `debug` parameter to `True`.
        
        @exception thermod.common.ScriptError if the provided script cannot
            be found or executed
        """
        
        super().__init__(scale, t_ref, t_raw, calibration)
        
        if isinstance(script, list):
            self._script = deepcopy(script)
        elif isinstance(script, str):
            self._script = shlex.split(script, comments=True)
        else:
            raise TypeError('the script parameter must be string or list')
        
        if debug:
            logger.debug('appending {} to script command', ScriptThermometer.DEBUG_OPTION)
            self._script.append(ScriptThermometer.DEBUG_OPTION)
        
        logger.debug('checking executability of provided script')
        check_script(self._script[0])
        
        logger.debug('{} initialized with script: `{}`',
                     self.__class__.__name__,
                     self._script)
    
    def __repr__(self, *args, **kwargs):
        return '<{module}.{cls}({script!r}, {debug!r}, {scale!r}, calibration={calib!r})>'.format(
                    module=self.__module__,
                    cls=self.__class__.__name__,
                    script=self._script,
                    debug=(ScriptThermometer.DEBUG_OPTION in self._script),
                    scale=self._scale,
                    calib=self._calibrate)
    
    @property
    def raw_temperature(self):
        """Retrive the current temperature executing the script.
        
        The return value is a float number. Many exceptions can be raised
        if the script cannot be executed or if the script exits with errors.
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
            logger.debug('the output of temperature script lacks the `{}` item',
                         ScriptThermometer.JSON_TEMPERATURE)
            
            raise ScriptThermometerError('the temperature script has not '
                                         'returned the current temperature',
                                         str(ke), self._script[0])
            
        except (ValueError, TypeError) as vte:  # error converting to float
            logger.debug('cannot convert temperature `{}` to number', tstr)
            raise ScriptThermometerError('the temperature script returned an '
                                         'invalid value', str(vte),
                                         self._script[0])
        
        # No round(t, 2) on returned value becasue the external script can be
        # connected to a very sensitive and calibrated thermometer.
        logger.debug('current temperature: {:.2f}', t)
        return t


if SpiDev:
    logger.debug('spidev module imported, defining custom MCP3008 class')
    
    class _MCP3008(object):
        def __init__(self, device, channel):
            self._device = device
            self.channel = channel
        
        @property
        def value(self):
            raw = self._device.xfer2([1, (8 + self.channel) << 4, 0])
            data = ((raw[1] & 3) << 8) + raw[2]
            return (data / 1023.0)
        
        def close(self):
            # do nothing, here only for compatibility with gpiozero.MCP3008 class
            pass
        
        @property
        def _spi(self):
            # here only for compatibility with gpiozero.MCP3008
            return self
    
    class _SpiDeviceWrapper(object):
        def __init__(self, bus=0, device=0):
            self.spi = SpiDev()
            self.bus = bus
            self.device = device
            #self.spi.open(bus, device)
            #self.spi.max_speed_hz = 15200
        
        def __del__(self):
            self.spi.close()
        
        def __call__(self, channel):
            if self.spi.fileno() == -1:
                self.spi.open(self.bus, self.device)
            
            return _MCP3008(self.spi, channel)
    
    # TODO documentare, ma vale usare un'implementazione custom per velocizzare l'avvio?
    MCP3008 = _SpiDeviceWrapper()


if MCP3008:  # either custom MCP3008 or gpiozero.MCP3008 are defined
    # IMPORTANT: for any new classes defined here, a fake one must be defined
    # in else section!
    
    logger.debug('defining specific classes for Raspberry Pi thermometer')

    # TODO inserire documentazione su come creare questa board con TMP36 e su
    # come viene misurata la temperatura facendo la media di più valori.
    class PiAnalogZeroThermometer(BaseThermometer):
        """Read temperature from a Raspberry Pi AnalogZero board in celsius degree.
        
        If a single channel is provided during object creation, it's value is used
        as temperature, if more than one channel is provided, the current
        temperature is computed averaging the values of all channels.
        
        @see http://rasp.io/analogzero/
        """
        
        def __init__(self, channels, scale=BaseThermometer.DEGREE_CELSIUS, t_ref=[], t_raw=[], calibration=None):
            """Init PiAnalogZeroThermometer object using `channels` of the A/D converter.
            
            @param channels the list of channels to read value from
            @param scale degree scale to be used
            @param t_ref list of reference values for temperature calibration
            @param t_raw list of raw temperatures read by the thermometer
                corresponding to values in `t_ref`
            @param calibration e callable object to calibrate the temperature
                (if both `t_ref` and `t_raw` are valid, this parameter is
                ignored)
            
            @exception ValueError if no channels provided or channels out of range [0,7]
            @exception ThermometerError if the module `gpiozero' cannot be imported
            """
            
            super().__init__(scale, t_ref, t_raw, calibration)
            
            if len(channels) == 0:
                raise ValueError('missing input channel for PiAnalogZero thermometer')
            
            for c in channels:
                if c < 0 or c > 7:
                    raise ValueError('input channels for PiAnalogZero must be in range 0-7, {} given'.format(c))
            
            self._vref = ((3.32/(3.32+7.5))*3.3*1000)
            
            logger.debug('init A/D converter with channels {}', channels)
            self._adc = [MCP3008(channel=c) for c in channels]
            
            # Set max comunication speed with the SPI device.
            # It's enough to set only for first MCP3008 object because every
            # MCP3008 object share the same SPI device (both mine and gpiozero
            # implementations). From my tests I have stated that 15200 Hz is
            # the best frequency to read temperature from TMP36 thermometer
            # connected through a MCP3008 A/D converter.
            try:
                self._adc[0]._spi._device.max_speed_hz = 15200
            except AttributeError:
                # Cannot set a custom communication speed because software bus
                # of gpiozero package is in use.
                logger.debug('PiAnalogZero thermometer is using gpiozero software bus to SPI device')
            
            # Only the first time an ubnormal raw temperature is read a warning
            # message is printed. This variable is used as a check for it.
            self._printed_warning_std = False
            
            # Allocate the queue for the last 30 temperatures to be averaged. The
            # value `30` covers a period of 3 minutes because the sleep time between
            # two measures is 6 seconds: 6*30 = 180 seconds = 3 minutes.
            self._temperatures = deque([self.realtime_raw_temperature], maxlen=30)
            
            # start averaging thread
            self._stop = Event()
            self._averaging_thread = Thread(target=self._update_temperatures, daemon=True)
            self._averaging_thread.start()
            
        
        def __repr__(self, *args, **kwargs):
            return '<{module}.{cls}({channels!r}, {scale!r}, calibration={calib!r})>'.format(
                        module=self.__module__,
                        cls=self.__class__.__name__,
                        channels=[adc.channel for adc in self._adc],
                        scale=self._scale,
                        calib=self._calibrate)
        
        def __deepcopy__(self, memodict={}):
            """Return a deep copy of this PiAnalogZeroThermometer."""
            return self.__class__(channels=[adc.channel for adc in self._adc],
                                  scale=self._scale,
                                  calibration=self._calibrate)
        
        @property
        def realtime_raw_temperature(self):
            """The current raw temperature as measured by physical thermometer.
            
            If more than one channel is provided during object creation, the
            returned temperature is the average value computed on all channels.
            """
            
            temperatures = [(((adc.value * self._vref) - 500) / 10) for adc in self._adc]
            
            std = numpy.std(temperatures)
            if std <= 1 and self._printed_warning_std is True:
                self._printed_warning_std = False
            
            elif std > 1 and self._printed_warning_std is False:
                self._printed_warning_std = True
                logger.warning('standard deviation of raw temperatures is {:.2f}, '
                               'greater than maximum allowed value, the '
                               'temperatures are {}'.format(std, temperatures))
            
            # the median exludes a possible single outlier
            return round(numpy.median(temperatures), 2)  # additional decimal are meaningless
        
        def _update_temperatures(self):
            """Start a cycle to update the list of last measured temperatures.
            
            This method should be run in a separate thread in order to keep
            the list `self._temperatures` always updated with the last measured
            temperatures.
            """
            
            logger.debug('starting temperature updating cycle')
            
            while not self._stop.wait(6):
                temp = self.realtime_raw_temperature
                self._temperatures.append(temp)
                logger.debug('added new realtime temperature {:.2f}', temp)
        
        @property
        def raw_temperature(self):
            """Return the average of the last measured temperatures.
            
            The average is the way to reduce fluctuation in measurment. Precisely
            the least 5 and the greatest 5 temperatures are excluded, even this
            trick is to stabilize the returned value.
            """
            
            logger.debug('retriving current raw temperature')
            
            skip = 5  # least and greatest temperatures to be excluded
            elements = len(self._temperatures)
            
            if elements < (2*skip + 1):
                shortened = self._temperatures
            
            else:
                temperatures = list(self._temperatures)
                temperatures.sort()
                shortened = temperatures[skip:(elements-skip)]
            
            return round(numpy.mean(shortened), 2)  # additional decimal are meaningless
        
        def __del__(self):
            """Stop the temperature-averaging thread."""
            # cannot use logger here, the logger could be already unloaded
            self._stop.set()
            self._averaging_thread.join(10)
            
            for adc in self._adc:
                adc.close()

else:
    # The running system is not a Raspberry Pi or both spidev and gpiozero
    # modules are not installed, in either cases fake Pi* classes are defined.
    # If an object of the following classes is created, an exception is raised.
    
    logger.debug('modules spidev and gpiozero not found, '
                 'probably the running system is not a Raspberry Pi')
    
    class PiAnalogZeroThermometer(BaseThermometer):
        def __init__(self, *args, **kwargs):
            raise ThermometerError('modules spidev and gpiozero not loaded')

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
