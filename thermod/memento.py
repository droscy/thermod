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
__updated__ = '2016-02-25'

logger = logging.getLogger(__name__)


def memento(obj, deep=True):
    """Return a function to restore the original state of an object."""
    
    state = (copy.deepcopy if deep else copy.copy)(obj.__dict__)
    
    def restore():
        obj.__dict__.clear()
        obj.__dict__.update(state)
    
    return restore


def transactional(method):
    """If the decorated method fails the old state is restored."""
    
    def wrapper(self, *args, **kwargs):
        restore = memento(self)
        
        try:
            return method(self, *args, **kwargs)
        
        except:
            restore()
            raise
    
    return wrapper
