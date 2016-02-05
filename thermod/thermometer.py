"""Interface to the thermometer."""

import logging
import subprocess
from copy import deepcopy

__date__ = '2016-02-04'
__updated__ = '2016-02-05'

logger = logging.getLogger(__name__)


def celsius2fahrenheit(value):
    return ((1.8 * value) + 32.0)

def fahrenheit2celsius(value):
    return ((value - 32.0) / 1.8)

# TODO documentare tutto
# TODO scrivere test suite


class ThermometerError(RuntimeError):
    """Main exception for thermomter-related errors.
    
    The attribute `suberror` can contain additional informations about the
    error. These informations are not printed nor returned by default and
    must be accessed directly.
    """
    
    def __init__(self, error=None, suberror=None):
        super().__init__(error)
        self.suberror = suberror


class BaseThermometer(object):

    DEGREE_CELSIUS = 'C'
    DEGREE_FAHRENHEIT = 'F'
    
    def __init__(self, scale=BaseThermometer.DEGREE_CELSIUS):
        logger.debug('initializing %s with %s degrees',
                     self.__class__.__name__,
                     ((scale == BaseThermometer.DEGREE_CELSIUS)
                        and 'celsius'
                        or 'fahrenheit'))
        
        self._scale = scale
    
    def __repr__(self, *args, **kwargs):
        return "{}.{}('{}')".format(self.__module__,
                                    self.__class__.__name__,
                                    self._scale)
    
    @property
    def temperature(self):
        raise NotImplementedError()
    
    def __str__(self, *args, **kwargs):
        return '{:.2f} °{}'.format(self.temperature, self._scale)
    
    def __format__(self, format_spec, *args, **kwargs):
        return '{:{}}'.format(self.temperature, format_spec)
    
    def to_celsius(self):
        if self._scale == self.DEGREE_CELSIUS:
            return self.temperature
        else:
            return fahrenheit2celsius(self.temperature)
    
    def to_fahrenheit(self):
        if self._scale == self.DEGREE_FAHRENHEIT:
            return self.temperature
        else:
            return celsius2fahrenheit(self.temperature)


class ScriptThermometer(BaseThermometer):
    # TODO anche qui si dovrebbe usare debug e l'output in json
    
    def __init__(self, script, scale=BaseThermometer.DEGREE_CELSIUS, debug=False):
        super().__init__(scale)
        
        if isinstance(script, list):
            self._script = deepcopy(script)
            self._shell = False
            
            if debug:
                self._script.append('--debug')
            
        elif isinstance(script, str):
            if debug:
                self._script = '{} --debug'.format(script)
            else:
                self._script = script
            
            self._shell = True
        
        else:
            raise TypeError('the script parameter must be string or list')
        
        logger.debug('initialized with script: `%s`', self._script)
    
    @property
    def temperature(self):
        logger.debug('retriving current temperature')
        
        try:
            out = subprocess.check_output(self._script, shell=self._shell).decode('utf-8').strip()
            t = float(out)
        
        except subprocess.CalledProcessError as cpe:
            suberr = 'the temperature script exited with return code {}'.format(cpe.returncode)
            logger.debug(suberr)
            
            err = cpe.output.decode('utf-8')
            logger.debug(err)
            
            raise ThermometerError((err or suberr), suberr)
            
        except ValueError as ve:
            logger.debug('cannot convert temperature `%s` to number', out)
            raise ThermometerError('the temperature script returned an '
                                   'invalid value', str(ve))
        
        logger.debug('current temperature: %.4f', t)
        return t
