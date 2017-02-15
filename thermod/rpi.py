# -*- coding: utf-8 -*-
"""Specific classes for Raspberry Pi hardware.

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

import logging

from datetime import datetime
from threading import Thread, Event
from collections import deque

from .config import LogStyleAdapter
from .heating import BaseHeating, HeatingError
from .thermometer import BaseThermometer, ThermometerError

__date__ = '2017-02-13'
__updated__ = '2017-02-15'

logger = LogStyleAdapter(logging.getLogger(__name__))


try:
    # Try importing RPi.GPIO module, if succeded spcific classes for
    # Raspberry Pi are defined, otherwise fake classes are created in the
    # `except` section below.
    
    # IMPORTANT: for any new classes defined here, a fake one must be defined in except section!
    
    logger.debug('importing RPi.GPIO module')
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    
    # define custom variables for high and low level trigger to be used in
    # config module for config parsing
    HIGH = GPIO.HIGH
    LOW = GPIO.LOW
    
    class PiPinsRelayHeating(BaseHeating):
        """Use relays connected to GPIO pins to switch on/off the heating."""
        
        def __init__(self, pins, switch_on_level):
            """Init GPIO `pins` connected to relays.
            
            @param pins single pin or list of BCM GPIO pins to use
            @param switch_on_level GPIO trigger level to swith on the heating
            
            @exception ValueError if no pins provided or pin number out of range [0,27]
            @exception HeatingError if the module `RPi.GPIO' cannot be loaded
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
            
            if switch_on_level == GPIO.HIGH:
                logger.debug('setting HIGH level to switch on the heating')
                self._on = GPIO.HIGH
                self._off = GPIO.LOW
            else:
                logger.debug('setting LOW level to switch on the heating')
                self._on = GPIO.LOW
                self._off = GPIO.HIGH
            
            logger.debug('initializing GPIO pins {}', self._pins)
            GPIO.setup(self._pins, GPIO.OUT)
            GPIO.output(self._pins, self._off)
        
        def __repr__(self, *args, **kwargs):
            return '{module}.{cls}({pins!r}, {level!r}'.format(
                        module=self.__module__,
                        cls=self.__class__.__name__,
                        pins=self._pins,
                        level=self._on)
        
        def switch_on(self):
            """Switch on the heating setting right level to GPIO pins."""
            logger.debug('switching on the heating')
            GPIO.output(self._pins, self._on)
        
        def switch_off(self):
            """Switch off the heating setting right level to GPIO pins."""
            logger.debug('switching off the heating')
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
            return '{module}.{cls}({channels!r}, {multiplier!r}, {shift!r}, {scale!r})'.format(
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
                logger.debug('appending new realtime temperature')
                self._temperatures.append(self.realtime_temperature)
        
        @property
        def temperature(self):
            """Return the average of the last measured temperatures.
            
            The average is the way to reduce fluctuation in measurment. Precisely
            the least 5 and the greatest 5 temperatures are excluded, even this
            trick is to stabilize the returned value.
            """
            
            logger.debug('retriving current temperature')
            
            temperatures = list(self._temperatures)
            temperatures.sort()
            
            skip = 5
            shortened = temperatures[skip:(len(temperatures)-skip)]
            
            return round(sum(shortened) / len(shortened), 4)  # addtition decimal are meaningless
        
        def __del__(self):
            """Stop the temperature-averaging thread."""
            # cannot use logger here, the logger could be already unloaded
            self._stop.set()
            self._averaging_thread.join(6)


except ImportError as ie:
    # The running system is not a Raspberry Pi or the RPi.GPIO module is not
    # installed, in both case fake Pi* classes are defined. If an object of the
    # following classes is created, an exception is raised.
    
    logger.debug('module RPi.GPIO not found, probably the running system is not a Raspberry Pi')
    
    # fake variables
    HIGH = 1
    LOW = 0
    
    # fake classes
    class PiPinsRelayHeating(BaseHeating):
        def __init__(self, *args, **kwargs):
            raise HeatingError('module RPi.GPIO not loaded')
    
    class PiAnalogZeroThermometer(BaseThermometer):
        def __init__(self, *args, **kwargs):
            raise ThermometerError('module RPi.GPIO not loaded')


# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab