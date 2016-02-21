"""Interface to the thermometer."""

import sys
import json
import shlex
import logging
import subprocess
from copy import deepcopy
#from json.decoder import JSONDecodeError
from .config import ScriptError

# backward compatibility for Python 3.4 (TODO check for better handling)
if sys.version[0:3] >= '3.5':
    from json.decoder import JSONDecodeError
else:
    JSONDecodeError = ValueError

__date__ = '2016-02-04'
__updated__ = '2016-02-21'

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
    return the current temperature as a float number.
    
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
        return "{}.{}('{}')".format(self.__module__,
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
    
    # TODO modificare questo come è stato modificato ScriptHeating con lo ScriptError
    
    DEBUG_OPTION = '--debug'
    JSON_TEMPERATURE = 'temperature'
    JSON_ERROR = 'error'
    
    def __init__(self, script, debug=False, scale=BaseThermometer.DEGREE_CELSIUS):
        super().__init__(scale)
        
        if isinstance(script, list):
            self._script = deepcopy(script)
        elif isinstance(script, str):
            self._script = shlex.split(script, comments=True)
        else:
            raise TypeError('the script parameter must be string or list')
        
        if debug:
            self._script.append(ScriptThermometer.DEBUG_OPTION)
        
        logger.debug('%s initialized with script: `%s`',
                     self.__class__.__name__,
                     self._script)
    
    def __repr__(self, *args, **kwargs):
        return "{module}.{cls}({script}, {debug}, {scale})".format(
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
