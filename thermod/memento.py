"""Custom implementation of Memento pattern.

We use a decorator function to confer transactional behaviour to methods
of classes in order to restore original state in case of exceptions.

The original implementation of this Memento pattern is described here
http://code.activestate.com/recipes/413838/ while a full implementation of
the Memento pattern can be found here
https://benzidwael.wordpress.com/2014/12/13/memento-design-pattern-part-2/.
"""

import copy
import logging

__date__ = '2016-02-25'
__updated__ = '2016-03-19'

logger = logging.getLogger(__name__)

# TODO finire messaggi di log
# TODO controllare che con l'exclude funzioni bene, e forse fare in modo
# che '_lock' venga aggiunto e non sia semplicemente il valore di default


def memento(obj, deep=True, exclude=['_lock']):
    """Return a function to restore the original state of an object."""
    
    #state = (copy.deepcopy if deep else copy.copy)(obj.__dict__)
    
    state = (copy.deepcopy if deep else copy.copy)({key: value for (key, value) in obj.__dict__.items() if key not in exclude})
    
    def restore():
        logger.debug('restoring old state of %s', obj)
        #obj.__dict__.clear()  # TODO assicurarsi che così non serva più
        # TODO cosa fa l'update? Sovrascrivere quelli esistente o inserisce solo quelli nuovi?
        obj.__dict__.update(state)
    
    return restore


def transactional(method):
    """If the decorated method fails the old state is restored."""
    
    # TODO forse meglio chiamare obj invece di self, così non ci si confonde
    def wrapper(self, *args, **kwargs):
        logger.debug('executing transactional method %r', method)
        restore = memento(self)
        
        try:
            result = method(self, *args, **kwargs)
        
        except:
            logger.debug('transaction aborted')
            restore()
            raise
        
        logger.debug('transaction completed')
        return result
    
    return wrapper
