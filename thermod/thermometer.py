# -*- coding: utf-8 -*-
"""Interface to the thermometer.

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

import json
import shlex
import logging
import subprocess
import statistics
import asyncio
import functools

from copy import deepcopy
from json.decoder import JSONDecodeError
from collections import deque
from random import random

from . import config
from .common import ScriptError, LogStyleAdapter, check_script, \
    DEGREE_CELSIUS, DEGREE_FAHRENHEIT, DEGREE_SCALE_LIST

try:
    from spidev import SpiDev
except ImportError:
    SpiDev = False
    try:
        from gpiozero import MCP3008
    except ImportError:
        MCP3008 = False

__date__ = '2016-02-04'
__updated__ = '2020-10-30'

logger = LogStyleAdapter(logging.getLogger(__name__))


# functions

def celsius2fahrenheit(value):
    """Convert celsius temperature to fahrenheit degrees."""
    return ((1.8 * value) + 32.0)

def fahrenheit2celsius(value):
    """Convert fahrenheit temperature to celsius degrees."""
    return ((value - 32.0) / 1.8)

def linearfit(raw, ref):
    """Return the transformation function to map `raw` values in `ref` values.
    
    The two imput must be lists with the same number of elements.
    
    @return a function that accept a single input and return the transformed output
    @exception IndexError if the two input lists have different number of elements
    
    @see https://en.wikipedia.org/wiki/Simple_linear_regression for explanation
    """
    
    if len(raw) != len(ref):
        raise IndexError('raw and ref lists have different number of elements')
    
    n = len(raw)
    
    sx = sum(raw)
    sy = sum(ref)
    sxx = sum([x**2 for x in raw])
    syy = sum([y**2 for y in ref])
    sxy = sum([raw[i]*ref[i] for i in range(n)])
    
    a = (n*sxy - sx*sy) / (n*sxx - sx**2)
    b = sy/n - a*sx/n
    
    return lambda x: a*x + b


# errors/exceptions

class ThermometerError(RuntimeError):
    """Main exception for thermomter-related errors.
    
    The attribute `suberror` can contain additional information about the
    error. This information is not printed nor returned by default and
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


# thermometers

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
    have the same number of elements and must have at least 2 elements each.
    To disable the calibration or to get the values for `t_raw` list, leave
    `t_raw` itself empty.
    """
    
    def __init__(self, scale, t_ref=[], t_raw=[], calibration=None):
        """Init the thermometer with a choosen degree scale.
        
        @param scale degree scale to be used
        @param t_ref list of reference values for temperature calibration
        @param t_raw list of raw temperatures read by the thermometer
            corresponding to values in `t_ref`
        @param calibration e callable object to calibrate the temperature (if
            both `t_ref` and `t_raw` are valid, this parameter is ignored)
        """
        
        if scale not in DEGREE_SCALE_LIST:
            raise ValueError('invalid degree scale {}'.format(scale))
        
        logger.debug('initializing {} with {} degrees',
                     self.__class__.__name__,
                     ('celsius' if scale == DEGREE_CELSIUS else 'fahrenheit'))
        
        self._scale = scale
        
        if len(t_raw) >= 2:
            if len(t_ref) == len(t_raw):
                logger.debug('performing thermometer calibration with t_ref={} and t_raw={}', t_ref, t_raw)
                self._calibrate = linearfit(t_raw, t_ref)
                logger.debug('calibration completed')
            else:
                raise ThermometerError('cannot perform thermometer calibration '
                                       'because t_ref and t_raw have different '
                                       'number of elements')
        elif calibration is not None:
            logger.debug('using external function to calibrate raw temperatures')
            self._calibrate = calibration
        else:
            logger.debug('calibration disabled due to t_raw list empty or too small')
            self._calibrate = lambda x: x
    
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
    async def raw_temperature(self):
        """This method must be implemented in subclasses.
        
        The subclasses' methods must return the current temperature read from
        the thermometer as a float number in the scale selected during class
        instantiation in order to correctly handle conversion methods and must
        raise `ThermometerError` in case of failure.
        
        No calibration adjustment must be performed in this method.
        
        @exception ThermometerError if an error occurred in retrieving temperature
        """
        
        raise NotImplementedError()
    
    @property
    async def temperature(self):
        """The calibrated temperature."""
        return round(self._calibrate(await self.raw_temperature), 2)  # additional decimal are meaningless
    
    def close(self):
        """To be implemented in subclasses to handle possible hardware shutdown."""
        pass


class FakeThermometer(BaseThermometer):
    """Fake thermometer that always returns 20.0 degrees celsius or 68.0 fahrenheit."""
    
    def __init__(self, scale=DEGREE_CELSIUS):
        super().__init__(scale)
    
    @property
    async def raw_temperature(self):
        t = 20.0
        if self._scale == DEGREE_CELSIUS:
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
    
    def __init__(self, script, debug=False, scale=DEGREE_CELSIUS, t_ref=[], t_raw=[], calibration=None):
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
    async def raw_temperature(self):
        """Retrive the current temperature executing the script.
        
        The returned value is a float number. Many exceptions can be raised
        if the script cannot be executed or if the script exits with errors.
        """
        
        logger.debug('retrieving current temperature')
        tstr = ''  # must be defined in case TypeError raised before assignment
        
        try:
            loop = asyncio.get_running_loop()
        
        except:
            loop = asyncio.get_event_loop()
        
        try:
            raw = await loop.run_in_executor(None, functools.partial(subprocess.check_output, self._script, shell=False))
            out = json.loads(raw.decode('utf-8'))
            
            tstr = out[ScriptThermometer.JSON_TEMPERATURE]
            t = float(tstr)
        
        except subprocess.CalledProcessError as cpe:  # error in subprocess
            suberr = 'the thermometer script exited with return code {}'.format(cpe.returncode)
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
            logger.debug('the thermometer script output is not in JSON format')
            raise ScriptThermometerError('script output is invalid, cannot get '
                                         'current temperature', str(jde),
                                         self._script[0])
        
        except KeyError as ke:  # error in retrieving element from out dict
            logger.debug('the output of thermometer script lacks the `{}` item',
                         ScriptThermometer.JSON_TEMPERATURE)
            
            raise ScriptThermometerError('the thermometer script has not '
                                         'returned the current temperature',
                                         str(ke), self._script[0])
            
        except (ValueError, TypeError) as vte:  # error converting to float
            logger.debug('cannot convert temperature `{}` to number', tstr)
            raise ScriptThermometerError('the temperature script returned an '
                                         'invalid value', str(vte),
                                         self._script[0])
        
        logger.debug('current temperature is {:.2f}', t)
        return t


if SpiDev:  # spidev module imported
    class _Light_MCP3008(object):
        """Custom lighter implementation of MCP3008 A/D converter.
        
        This class is a reimplementation of gpiozero.MCP3008 class and permits a
        fast loading of thermod package on systems with limited resources (like
        the Raspberry Pi Zero) without loading the whole `gpiozero` package.
        """
    
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
        """A wrapper around a SPI device to share the same device between multiple objects."""
        
        def __init__(self, bus=0, device=0):
            self.spi = SpiDev()
            self.bus = bus
            self.device = device
        
        def __del__(self):
            self.spi.close()
        
        def __call__(self, channel):
            if self.spi.fileno() == -1:
                self.spi.open(self.bus, self.device)
            
            return _Light_MCP3008(self.spi, channel)
    
    # replacement of `gpiozero.MPC3008` class interface
    MCP3008 = _SpiDeviceWrapper()


class _fake_RPi_Device(object):
    """Fake class to test Raspberry Pi boards without the real hardware."""
    def __init__(self):
        self.max_speed_hz = None

class _fake_RPi_SpiDev(object):
    """Fake class to test Raspberry Pi boards without the real hardware."""
    _device = _fake_RPi_Device()

class _fake_RPi_MCP3008(object):
    """Fake class to test Raspberry Pi boards without the real hardware."""
    
    _spi = _fake_RPi_SpiDev()
    
    def __init__(self, channel):
        self.channel = channel
    
    @property
    def value(self):
        d = 0.004937934  # 0.5° C
        r = (random() * d) - (d / 2)  # a value between -0.25° and +0.25° C
        return (0.691310697 + r)  # 20° ± 0.25° C
    
    def close(self):
        pass


# TODO inserire documentazione su come creare questa board con TMP36 e su
# come viene misurata la temperatura prendendo la mediana dei valori.
class PiAnalogZeroThermometer(BaseThermometer):
    """Read temperature from a Raspberry Pi AnalogZero board in celsius degree.
    
    If a single channel is provided during object creation, it's value is used
    as temperature, if more than one channel is provided, the current
    temperature is computed getting the median value of all channels.
    
    @see http://rasp.io/analogzero/
    """
    
    def __init__(self,
                 channels,
                 scale=DEGREE_CELSIUS,
                 t_ref=[],
                 t_raw=[],
                 stddev=2.0,
                 calibration=None):
        """Init PiAnalogZeroThermometer object using `channels` of the A/D converter.
        
        @param channels the list of channels to read value from
        @param scale degree scale to be used
        @param t_ref list of reference values for temperature calibration
        @param t_raw list of raw temperatures read by the thermometer
            corresponding to values in `t_ref`
        @param stddev maximum standard deviation between temperatures to
            consider a thermometer not broken
        @param calibration a callable object to calibrate the temperature
            (if both `t_ref` and `t_raw` are valid, this parameter is
            ignored)
        
        @exception ValueError if no channels provided or channels out of range [0,7]
        @exception ThermometerError if the module `gpiozero' cannot be imported
        """
        
        super().__init__(scale, t_ref, t_raw, calibration)
        
        if not isinstance(channels, list):
            raise TypeError('channels must be a list of integers in range 0-7')
        
        if len(channels) == 0:
            raise ValueError('missing input channel(s) for PiAnalogZero thermometer')
        
        for c in channels:
            try:
                if c < 0 or c > 7:
                    raise ValueError('input channels for PiAnalogZero must be '
                                     'in range 0-7, {} given'.format(c))
            
            except TypeError:
                raise TypeError('input channels for PiAnalogZero must be '
                                'integers in range 0-7, {} given'.format(c))
        
        # voltage reference value
        self._vref = ((3.32/(3.32+7.5))*3.3*1000)
            
        # If the config variable '_fake_RPi_Thermometer' is True, fake
        # implementation for MCP3008 class is used in order to test
        # Raspberry Pi thermometer without requiring the real hardware.
        if config._fake_RPi_Thermometer:
            logger.debug('using a fake implementation for gpiozero.MCP3008 class')
            _MCP3008 = _fake_RPi_MCP3008
        
        # Otherwise, if the real MCP3008 class is not defined (i.e. one of the
        # required modules cannot be loaded), an exception is raised.
        elif MCP3008 is False:
            raise ThermometerError('modules spidev and gpiozero not loaded',
                                   'the MCP3008 class is not defined, we are '
                                   'not on Raspberry Pi or neither spidev nor '
                                   'gpiozero modules are available')
        
        # Otherwise the real MCP3008 class is used.
        else:
            _MCP3008 = MCP3008
        
        logger.debug('init A/D converter with channels {}', channels)
        self._adc = [_MCP3008(channel=c) for c in channels]
        
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
        
        self._stddev = stddev
        
        # Only the first time an abnormal raw temperature is read a warning
        # message is printed. This variable is used as a check for it.
        self._printed_warning_std = False
        
        logger.debug('{} initialized', self.__class__.__name__)
    
    def __repr__(self, *args, **kwargs):
        return ('<{module}.{cls}({channels!r}, {scale!r}, '
                'stddev={stddev!r}, calibration={calib!r})>'.format(
                    module=self.__module__,
                    cls=self.__class__.__name__,
                    channels=[adc.channel for adc in self._adc],
                    scale=self._scale,
                    stddev=self._stddev,
                    calib=self._calibrate))
    
    def __deepcopy__(self, memodict={}):
        """Return a deep copy of this PiAnalogZeroThermometer."""
        return self.__class__(channels=[adc.channel for adc in self._adc],
                              scale=self._scale,
                              stddev=self._stddev,
                              calibration=self._calibrate)
    
    @property
    async def raw_temperature(self):
        """The current raw temperature as measured by physical thermometer.
        
        If more than one channel is provided during object creation, the
        returned temperature is the median value of all channels (the mean
        value if there are only two channels).
        
        A standard deviation between all values is also used to exclude from
        the computation broken physical thermometers.
        """
        
        logger.debug('retrieving temperatures from A/D converter')
        temperatures = [(((adc.value * self._vref) - 500) / 10) for adc in self._adc]
        
        logger.debug('checking standard deviation of temperatures {}', temperatures)
        
        # This if-else block is the same of Wire1Thermometer except the error messages,
        # remember to modify both.
        if len(temperatures) > 0:
            std = statistics.pstdev(temperatures)
            
            logger.debug('standard deviation is {:.2f} maximum allowed value is {:.2f}', std, self._stddev)
            
            if std < self._stddev and self._printed_warning_std is True:
                self._printed_warning_std = False
            
            elif std >= self._stddev and self._printed_warning_std is False:
                self._printed_warning_std = True
                logger.warning('standard deviation of temperatures {} is {:.2f}, '
                               'greater than the maximum allowed value of {:.2f}',
                               [round(t, 2) for t in temperatures], std, self._stddev)
            
            # the median excludes a possible single outlier
            raw = statistics.median(temperatures)
            logger.debug('current median of temperatures is {:.2f}', raw)
        
        else:
            raise ThermometerError('no temperature retrieved, probably all '
                                   'thermometers are not ready or unavailable')
        
        logger.debug('returning A/D temperature ({:.2f})', raw)
        return round(raw, 4)  # additional decimals are meaningless (MCP3008 is not so sensitive)
    
    def __del__(self):
        """Close hardware channels."""
        # cannot use logger here, the logger could be already unloaded
        try:
            for adc in self._adc:
                adc.close()
        except AttributeError:
            # an exception was raised in __init__() method, the object is incomplete
            pass


class OneWireThermometer(BaseThermometer):
    """Read temperatures from 1-Wire thermometers like DS18B20."""
    
    def __init__(self,
                 devices,
                 scale=DEGREE_CELSIUS,
                 t_ref=[],
                 t_raw=[],
                 stddev=2.0,
                 calibration=None):
        """Init OneWireThermometer object reading temperatures from `devices`.
        
        @param devices the list of 1-Wire devices to read the temperature from
            (the devices are in /sys/bus/w1/devices folder) or a list of full
            paths to 'w1_slave' files
        @param scale degree scale to be used
        @param t_ref list of reference values for temperature calibration
        @param t_raw list of raw temperatures read by the thermometer
            corresponding to values in `t_ref`
        @param stddev maximum standard deviation between temperatures to
            consider a thermometer not broken
        @param calibration a callable object to calibrate the temperature
            (if both `t_ref` and `t_raw` are valid, this parameter is
            ignored)
        
        @exception ValueError if no devices provided
        @exception FileNotFoundError if the device cannot be read
        """
        
        super().__init__(scale, t_ref, t_raw, calibration)
        
        if not isinstance(devices, list):
            raise TypeError('devices must be a list of strings')
        
        if len(devices) == 0:
            raise ValueError('missing 1-Wire devices to read temperature from')
        
        self._devices = []
        
        for dev in devices:
            path = (dev if dev[0] == '/' else '/sys/bus/w1/devices/{}/w1_slave'.format(dev))
            with open(path, 'r'):
                self._devices.append(path)
        
        self._stddev = stddev
        
        # Only the first time an abnormal raw temperature is read a warning
        # message is printed. This variable is used as a check for it.
        self._printed_warning_std = False
        
        logger.debug('{} initialized with devices: `{}`',
                     self.__class__.__name__,
                     self._devices)
    
    def __repr__(self, *args, **kwargs):
        return ('<{module}.{cls}({devices!r}, {scale!r}, '
                'stddev={stddev!r}, calibration={calib!r})>'.format(
                    module=self.__module__,
                    cls=self.__class__.__name__,
                    devices=self._devices,
                    scale=self._scale,
                    stddev=self._stddev,
                    calib=self._calibrate))
    
    def _read_device_data(self, dev):
        """Open the 1-Wire device and read its data.
        
        This can be a long blocking I/O operation and thus it will be
        executed in different thread of the main asyncio loop.
        """
        
        with open(dev, 'r') as f:
            data = f.readlines()
        
        return data
    
    @property
    async def raw_temperature(self):
        """The current raw temperature as measured by physical thermometer.
        
        If more than one device is provided during object creation, the
        returned temperature is the median value of all devices (the mean
        value if there are only two devices).
        
        A standard deviation between all values is also used to exclude from
        the computation broken physical thermometers.
        """
        
        logger.debug('retrieving temperature from 1-Wire devices')
        
        temperatures = []
        
        try:
            loop = asyncio.get_running_loop()
        
        except:
            loop = asyncio.get_event_loop()
        
        for dev in self._devices:
            try:
                with open(dev, 'r') as f:
                    data = f.readlines()
                
                data = await loop.run_in_executor(None, self._read_device_data, dev)
                
                if data[0].strip()[-3:] == 'YES':
                    temperatures.append(float(data[1].split("=")[1]) / 1000)
                
                else:
                    logger.warning('1-wire device {} not ready, keep going without it', dev)
                
            except IOError as ioe:
                logger.warning('cannot access 1-wire device {}: {}', dev, ioe)
                logger.info('keep going without device {}', dev)
        
        logger.debug('checking standard deviation of temperatures {}', temperatures)
        
        # This if-else block is the same of PiAnalogZeroThermometer except the error messages,
        # remember to modify both.
        if len(temperatures) > 0:
            std = statistics.pstdev(temperatures)
            
            logger.debug('standard deviation is {:.2f} maximum allowed value is {:.2f}', std, self._stddev)
            
            if std < self._stddev and self._printed_warning_std is True:
                self._printed_warning_std = False
            
            elif std >= self._stddev and self._printed_warning_std is False:
                self._printed_warning_std = True
                logger.info('temperatures are {}', temperatures)
                logger.warning('standard deviation of temperatures is {:.2f}, '
                               'greater than the maximum allowed value of {:.2f}',
                               std, self._stddev)
            
            # the median excludes a possible single outlier
            raw = statistics.median(temperatures)
            logger.debug('current median of temperatures is {:.2f}', raw)
        
        else:
            raise ThermometerError('no temperature retrieved, probably all '
                                   '1-Wire devices are not ready or unavailable')
        
        logger.debug('returning 1-Wire temperature ({:.2f})', raw)
        return raw


class Wire1Thermometer(OneWireThermometer):
    """Read temperatures from 1-Wire thermometers like DS18B20.
    
    This class is now *deprecated*, please use `thermod.OneWireThermometer` instead.
    """
    
    def __init__(self,
                 devices,
                 scale=DEGREE_CELSIUS,
                 t_ref=[],
                 t_raw=[],
                 stddev=2.0,
                 calibration=None):
        logger.warning('Wire1Thermometer class is deprecated, please use OneWireThermometer')
        super.__init__(devices, scale, t_ref, t_raw, stddev, calibration)


# decorators

class ThermometerBaseDecorator(BaseThermometer):
    """Base decorator for subclasses of BaseThermometer.
    
    This class simply forwards any public method invocation to the decorated
    thermometer passed during object creation.
    """
    
    def __init__(self, thermometer):
        """Init the base decorator storing a reference to the decorated thermometer.
        
        @param thermometer the BaseThermometer to be decorated
        @exception TypeError in case `thermometer` is not an instance of BaseThermometer
        """
        
        logger.debug('initializing a new {}', self.__class__.__name__)
        
        if not isinstance(thermometer, BaseThermometer):
            raise TypeError('the provided thermometer is not an instance of {}'
                            .format(BaseThermometer.__class__.__name__))
        
        # private reference to the decorated thermometer
        self.__decorated = thermometer
        
        # Replicate internal _scale attribute that is used in to_celsius()
        # and to_fahrenheit() methods.
        self._scale = thermometer._scale
        
        # Replicate internal _calibrate method that is used in other methods.
        self._calibrate = thermometer._calibrate
    
    def __repr__(self, *args, **kwargs):
        return '<{}.{}({!r})>'.format(self.__module__,
                                      self.__class__.__name__,
                                      self.__decorated)
    
    @property
    def decorated(self):
        """Return the reference to the decorated thermometer."""
        return self.__decorated
    
    @property
    async def raw_temperature(self):
        #logger.debug('forwarding `raw_temperature` call from {} to {}',
        #             self.__class__.__name__,
        #             self.decorated.__class__.__name__)
        
        return await self.decorated.raw_temperature
    
    def close(self):
        #logger.debug('forwarding `close` call from {} to {}',
        #             self.__class__.__name__,
        #             self.decorated.__class__.__name__)
        
        self.decorated.close()


class ScaleAdapterThermometerDecorator(ThermometerBaseDecorator):
    """Adjust the degree scale of the thermometer to another scale.
    
    This decorator can be used when the thermometer reads temperature in
    a scale and the whole system wants another scale.
    """
    
    def __init__(self, thermometer, convert_to_scale):
        """Init this decorator to convert temperatures to `convert_to_scale`.
        
        @param thermometer the BaseThermometer to be decorated
        @param convert_to_scale the degree scale to convert temperatures to
        """
        
        super().__init__(thermometer)
        
        if convert_to_scale not in DEGREE_SCALE_LIST:
            raise ValueError('invalid degree scale `{}` to convert temperatures to'.format(convert_to_scale))
        
        self._to_scale = convert_to_scale
        
        if self.decorated._scale == self._to_scale:
            logger.debug('no conversion required, the system uses the same degree scale of the thermometer')
        
        else:
            logger.debug('converting all temperatures from {} to {}',
                         ('celsius' if self.decorated._scale == DEGREE_CELSIUS else 'fahrenheit'),
                         ('celsius' if self._to_scale == DEGREE_CELSIUS else 'fahrenheit'))
    
    def __repr__(self, *args, **kwargs):
        return '<{}.{}({!r}, {})>'.format(self.__module__,
                                          self.__class__.__name__,
                                          self.decorated,
                                          self._to_scale)
    
    @property
    async def raw_temperature(self):
        """Return the raw temperature converted to the wanted degree scale."""
        
        orig = await self.decorated.raw_temperature
        
        if (self.decorated._scale == DEGREE_CELSIUS
                and self._to_scale == DEGREE_FAHRENHEIT):
            converted = celsius2fahrenheit(orig)
            logger.debug('converting temperature {:.2f} to fahrenheit {:.2f}', orig, converted)
        
        elif (self.decorated._scale == DEGREE_FAHRENHEIT
                and self._to_scale == DEGREE_CELSIUS):
            converted = fahrenheit2celsius(orig)
            logger.debug('converting temperature {:.2f} to celsius {:.2f}', orig, converted)
        
        else:
            # no conversion required, no debug message
            converted = orig
        
        return converted


class SimilarityCheckerThermometerDecorator(ThermometerBaseDecorator):
    """Check if the last read temperature is similar to the average of older values.
    
    To do the check, a history of older temperatures is stored. Every new
    temperature is compared to the average value of the list, if it is similar,
    it is added to the list, otherwise an error is rised.
    
    **Note**: in case of joint usage of this decorator with an
    AveragingTaskThermometerDecorator, this one should be the *inner* decorator.
    """
    
    def __init__(self, thermometer, queuelen, delta):
        """Init SimilarityCheckerThermometerDecorator.
        
        @param thermometer the BaseThermometer to be decorated
        @param queuelen the number of older temperatures to keep
        @param delta the maximum allowed difference from new temperature to be
            considered similar to older values
        """
        super().__init__(thermometer)
        
        logger.debug('queue size is {}, maximum allowed delta is {} degrees', queuelen, delta)
        self.last_raw_temperatures = deque([self.decorated.raw_temperature],
                                           maxlen=queuelen)
        self.delta = delta
    
    def __repr__(self, *args, **kwargs):
        return '<{}.{}({!r}, {}, {})>'.format(self.__module__,
                                              self.__class__.__name__,
                                              self.decorated,
                                              self.last_raw_temperatures.maxlen,
                                              self.delta)
    
    @property
    async def raw_temperature(self):
        """Return the raw temperature only if it is similar to the average of older values.
        
        @exception ThermometerError when the just read value is NOT similar
        """
        
        newtemp = await self.decorated.raw_temperature
        avgtemp = statistics.mean(self.last_raw_temperatures)
        delta = abs(newtemp - avgtemp)
        
        logger.debug('new temperature is {:.2f}, old average value '
                     'is {:.2f}, delta is {:.2f}', newtemp, avgtemp, delta)
        
        if delta >= self.delta:
            raise ThermometerError('the just read temperature ({:.2f} degrees) '
                                   'has been ignored because it is more than {} '
                                   'degrees away from the average value of the '
                                   'previous temperatures ({:.2f} degrees)'
                                   .format(newtemp, self.delta, avgtemp),
                                   'this is probably a hardware fault')
        
        logger.debug('appending the new temperature to the similarity checker queue')
        self.last_raw_temperatures.append(newtemp)
        
        return newtemp


class AveragingTaskThermometerDecorator(ThermometerBaseDecorator):
    """Start a task that computes the average of temperatures in a long interval of time.
    
    Sometimes a thermometer can be very "noisy" due to fluctuation of currents
    or external perturbations. This decorator tries to mitigate this problem
    querying the thermometer at a fixed short interval of time and keeping all
    the temperatures for a long time. When the current temperature is retireved
    using the builtin `temperature` property, the average of the stored
    temperatures is returned, this is the mean value of the temperatures in the
    long period.
    
    The real thermometer is automatically queried using an asynchronous task.
    
    **Note**: in case of joint usage of this decorator with a
    SimilarityCheckerThermometerDecorator, this one should be the *outer*
    decorator.
    """
    
    def __init__(self,
                 thermometer,
                 short_interval=3,  # seconds
                 averaging_time=6,  # minutes
                 skipval=0.33,
                 loop=None):
        """Decorate `thermometer` with an autonomous averaging task.
        
        @param thermometer the BaseThermometer to be decorated
        @param short_interval time interval (in seconds) between two following
            query of the real thermometer
        @param averaging_time the reported temperature is the average
            of all temperatures read during this time (in minutes)
        @param skipval the percentage of temperatures to be skipped during
            the average process, the half of this value from the greatest
            temperatures and the other half form the lowest (this value
            must be between 0 and 1)
        @param loop the asynchronous loop to be used (if it is `None` the
            default loop as retrieved with `asyncio.get_running_loop()` is
            used)
        """
        
        super().__init__(thermometer)
        self._short_interval = short_interval
        self._averaging_time = averaging_time
        self._skipval = skipval
        
        # exception raised inside the averaging task (None == no exception)
        self._fail_exception = None
        
        # Allocate the queue for the last temperatures to be averaged. The
        # lenght is computed considering the desired averaging time and
        # the frequency of the raw samples.
        self._temperatures = deque([self.decorated.raw_temperature],
                                   maxlen=int(self._averaging_time * 60 / self._short_interval))
        
        # get the event loop
        if loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            
            except:
                self._loop = asyncio.get_event_loop()
        
        else:
            self._loop = loop
        
        # start averaging task
        self._averaging_task = None
        self._create_averaging_task()
    
    def __repr__(self, *args, **kwargs):
        return ('<{module}.{cls}(thermometer={decorated!r}, '
                'short_interval={shortint!r}, '
                'averaging_time={avgtime!r}, '
                'skipval={skipval!r}, '
                'loop={loop!r})>'.format(module=self.__module__,
                                         cls=self.__class__.__name__,
                                         decorated=self.decorated,
                                         shortint=self._short_interval,
                                         avgtime=self._averaging_time,
                                         skipval=self._skipval,
                                         loop=self._loop))
    
    def _create_averaging_task(self):
        """Create an averaging task if no task has already been created."""
        
        if self._averaging_task is None:
            logger.debug('creating averaging task')
            self._averaging_task = self._loop.create_task(self._update_temperatures())
            self._averaging_task.add_done_callback(self._update_temperatures_callback)
        
        else:
            logger.debug('an averaging task is already running')
    
    async def _update_temperatures(self):
        """Start a loop to update the list of last measured temperatures.
        
        This method should be run in a separate task in order to keep
        the list `self._temperatures` always updated with the last measured
        temperatures. To that task should be added as "done callback" function
        the method `self._update_temperatures_callback` to manage exceptions.
        
        @exception asyncio.CancelledError at the end of the task
        """
        
        logger.debug('starting temperature updating cycle')
        
        while True:
            temp = await self.decorated.raw_temperature
            self._temperatures.append(temp)
            logger.debug('added new temperature ({:.2f}) to the averaging queue', temp)
            await asyncio.sleep(self._short_interval, loop=self._loop)
    
    def _update_temperatures_callback(self, averaging_task):
        """Save the exceptions raised by `self._update_temperatures`."""
        
        try:
            averaging_task.result()
        
        except asyncio.CancelledError:
            logger.debug('temperature updating cycle stopped')
        
        except Exception as e:
            logger.debug('generic exception in temperature updating cycle')
            self._fail_exception = e
        
        finally:
            self._averaging_task = None
    
    @property
    async def raw_temperature(self):
        """Return a "weighted" average of the last measured temperatures.
        
        The average is computed excluding some greatest and lowest
        temperatures in the `self._temperatures` queue using `self._skipval`
        to compute how many temperatures to exclude.
        """
        
        logger.debug('retrieving average of last temperatures')
        
        if self._fail_exception is not None:
            # An exception has been raised inside the averaging task, we raise
            # that exception here in order to be propagated to the main loop,
            # then we reset the exception so the next call to this method
            # will recreate the averaging task.
            
            try:
                raise self._fail_exception
            
            finally:
                self._fail_exception = None
        
        else:
            self._create_averaging_task()
        
        skip = int(round(self._temperatures.maxlen * self._skipval / 2, 0))  # least and greatest temperatures to be excluded
        elements = len(self._temperatures)
        
        if elements < self._temperatures.maxlen:
            shortened = self._temperatures
        
        else:
            temperatures = list(self._temperatures)
            temperatures.sort()
            shortened = temperatures[skip:(elements-skip)]
        
        raw = statistics.mean(shortened)
        logger.debug('the average of last temperatures is {:.2f}', raw)
        return raw
    
    def close(self):
        """Stop the temperature updating task."""
        logger.debug('stopping temperature updating cycle')
        
        if self._averaging_task is not None:
            self._averaging_task.cancel()
        
        # forwarding the call to the decorated thermometer
        self.decorated.close()

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
