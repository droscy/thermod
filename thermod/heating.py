"""Interface to the real heating."""

import sys
import json
import logging
import subprocess

# backward compatibility for Python 3.4 (TODO check for better handling)
if sys.version[0:3] >= '3.5':
    from json.decoder import JSONDecodeError
else:
    JSONDecodeError = ValueError

__date__ = '2015-12-30'
__updated__ = '2016-01-08'

logger = logging.getLogger(__name__)

# TODO scrivere unit test
# TODO prevedere un last_on_time da salvare internamente


class HeatingError(RuntimeError):
    """Main exception for heating-related errors.
    
    The attribute `suberror` can contain additional informations about the
    error. These informations are not printed nor returned by default and
    must be accessed directly.
    """
    
    def __init__(self, error=None, suberror=None):
        super().__init__(error)
        self.suberror = suberror


class BaseHeating(object):
    """Abstract class that represents a real heating.
    
    To model your real heating sublcass this class and implement the
    three method `BaseHeating.switch_on()`, `BaseHeating.switch_off()`
    and `BaseHeating.status()`.
    """
    
    def switch_on(self):
        """Switch on the heating, on failure a `HeatingError` is raised.
        
        Subclasses must adhere this behaviour to be compatible.
        """
        raise NotImplementedError('the `switch_on` method is not implemented')
    
    def switch_off(self):
        """Switch off the heating, on failure a `HeatingError` is raised.
        
        Subclasses must adhere this behaviour to be compatible.
        """
        raise NotImplementedError('the `switch_off` method is not implemented')
    
    def status(self):
        """Return the status of the heating as integer: 1=ON, 0=OFF.
        
        Subclasses must adhere this behaviour to be compatible.
        """
        raise NotImplementedError('the `status` method is not implemented')


class ScriptHeating(BaseHeating):
    """Manage the real heating through three external scripts.
    
    The three scripts are the interfaces to the hardware of the heating:
    one to retrive the current status, one to switch on the heating and the
    last one to swith it off.
    
    The three scripts must be POSIX compliant and must exit with code
    0 on success and 1 on error. In addition they must write to the standard
    output a JSON string with the following fields:
    
        - `success`: if the operation has been completed successfully or not
          (boolean value `true` for success and `false` for failure);
        
        - `status`: the current status of the heating (as integer: 1=ON, 0=OFF);
        
        - `error`: the error message in case of failure, `null` or empty
          string otherwise.
    """
    
    SUCCESS = 'success'
    STATUS = 'status'
    ERROR = 'error'
    
    def __init__(self, switchon, switchoff, status):
        """Init the `ScriptHeating` object.
        
        The three parameters must be strings containing the full paths to the
        scripts with options (like `/usr/local/bin/switchoff -j -v`) or an
        array with the script to be executed followed by the options
        (like `['/usr/local/bin/switchoff', '-j', '-v']`).
        """
        
        self._switch_on = switchon
        self._switch_off = switchoff
        self._status = status
        
        if isinstance(self._switch_on, list):
            self._switchon_shell = False
        elif isinstance(self._switch_on, str):
            self._switchon_shell = True
        else:
            raise TypeError('the switchon parameter must be string or list')
        
        if isinstance(self._switch_off, list):
            self._switchoff_shell = False
        elif isinstance(self._switch_off, str):
            self._switchoff_shell = True
        else:
            raise TypeError('the switchoff parameter must be string or list')
        
        if isinstance(self._status, list):
            self._status_shell = False
        elif isinstance(self._status, str):
            self._status_shell = True
        else:
            raise TypeError('the status parameter must be string or list')
        
        logger.debug('{} initialized with ON=`{}`, OFF=`{}` and STATUS=`{}`'
                     .format(self.__class__.__name__,
                             self._switch_on,
                             self._switch_off,
                             self._status))
    
    def switch_on(self):
        """Switch on the heating executing the `switchon` script."""
        
        logger.debug('switching on the heating')
        
        try:
            subprocess.check_output(self._switch_on, shell=self._switchon_shell)
        
        except subprocess.CalledProcessError as cpe:
            suberr = 'the switch-on script exited with return code {}'.format(cpe.returncode)
            logger.debug(suberr)
            
            try:
                out = json.loads(cpe.output.decode('utf-8'))
            except:
                out = {ScriptHeating.ERROR: '{} and the output is invalid'.format(suberr)}
            
            if ScriptHeating.ERROR in out:
                err = str(out[ScriptHeating.ERROR])
                logger.debug(err)
            
            raise HeatingError((err or suberr), suberr)
        
        logger.debug('heating switched on')
    
    def switch_off(self):
        """Switch off the heating executing the `switchoff` script."""
        
        logger.debug('switching off the heating')
        
        try:
            subprocess.check_output(self._switch_off, shell=self._switchoff_shell)
        
        except subprocess.CalledProcessError as cpe:
            suberr = 'the switch-off script exited with return code {}'.format(cpe.returncode)
            logger.debug(suberr)
            
            try:
                out = json.loads(cpe.output.decode('utf-8'))
            except:
                out = {ScriptHeating.ERROR: '{} and the output is invalid'.format(suberr)}
            
            if ScriptHeating.ERROR in out:
                err = str(out[ScriptHeating.ERROR])
                logger.debug(err)
            
            raise HeatingError((err or suberr), suberr)
        
        logger.debug('heating switched off')
    
    def status(self):
        """Exec the `status` script and return the current status of the heating.
        
        The returned value is an integer: 1 for heating ON and 0 for OFF.
        """
        
        logger.debug('retriving the status of the heating')
        
        try:
            out = json.loads(subprocess.check_output(
                                self._status,
                                shell=self._status_shell).decode('utf-8'))
            
            ststr = out[ScriptHeating.STATUS]
            status = int(ststr)
        
        except subprocess.CalledProcessError as cpe:
            suberr = 'the status script exited with return code {}'.format(cpe.returncode)
            logger.debug(suberr)
            
            try:
                out = json.loads(cpe.output.decode('utf-8'))
            except:
                out = {ScriptHeating.ERROR: '{} and the output is invalid'.format(suberr)}
            
            if ScriptHeating.ERROR in out:
                err = str(out[ScriptHeating.ERROR])
                logger.debug(err)
            
            raise HeatingError((err or suberr), suberr)
        
        except JSONDecodeError as jde:
            logger.debug('the script output is not in JSON format')
            raise HeatingError('script output is invalid, cannot get current '
                               'status', str(jde))
        
        except KeyError as ke:
            logger.debug('the script output lacks the `{}` item'
                         .format(ScriptHeating.STATUS))
            
            raise HeatingError('the status script has not returned the '
                               'current heating status', str(ke))
            
        except ValueError as ve:
            logger.debug('cannot convert status `{}` to integer'.format(ststr))
            raise HeatingError('the status script returned an invalid status',
                               str(ve))
            
        logger.debug('the heating is currently {}'.format((status and 'ON' or 'OFF')))
        
        return status


# only for debug purpose
if __name__ == '__main__':
    heating = ScriptHeating('python3 scripts/switch.py --on -j',
                            'python3 scripts/switch.py --off -j',
                            'python3 scripts/switch.py --status -j')
    
    print('STATUS: {}'.format(heating.status() and 'ON' or 'OFF'))
    
    heating.switch_off()
    print('STATUS: {}'.format(heating.status() and 'ON' or 'OFF'))
    
    heating.switch_on()
    print('STATUS: {}'.format(heating.status() and 'ON' or 'OFF'))
    
    heating.switch_on()
    print('STATUS: {}'.format(heating.status() and 'ON' or 'OFF'))
