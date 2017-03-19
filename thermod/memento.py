# -*- coding: utf-8 -*-
"""Custom implementation of Memento pattern.

We use a decorator function to confer transactional behaviour to methods
of classes in order to restore original state in case of exceptions.

The original implementation of this Memento pattern is described here
http://code.activestate.com/recipes/413838/ while a full implementation of
the Memento pattern can be found here
https://benzidwael.wordpress.com/2014/12/13/memento-design-pattern-part-2/.

Copyright (C) 2005 Zoran Isailovski
Copyright (C) 2016 Simone Rossetto <simros85@gmail.com>
Python Software Foundation License
"""

import copy
import logging

__date__ = '2016-02-25'
__updated__ = '2016-03-27'
__version__ = '2.0'

logger = logging.getLogger(__name__)


def memento(obj, exclude=None, deep=True):
    """Return a function to restore the original state of an object.
    
    @param obj the object which to save the state of
    @param exclude a list of attributes name that do not have to be saved
        (empty list or `None` are accepted)
    @param deep if copy.deepcopy should be used to save the state
    """
    
    if exclude is None:
        exclude = []
    elif not isinstance(exclude, (list, tuple, dict)):
        exclude = [exclude,]
    
    state = (copy.deepcopy if deep else copy.copy)({key: value for (key, value) in obj.__dict__.items() if key not in exclude})
    
    def restore():
        logger.debug('restoring old state of %s', obj)
        #obj.__dict__.clear()  # commented out when exclude argument was added
        obj.__dict__.update(state)
    
    return restore


def transactional(exclude=None):
    """If the decorated method fails the old state is restored.
    
    This decorator needs a list of attributes that don't have to be restored,
    the list can also be empty or `None` if no exclusion is required.
    
    @param exclude a list of attributes name that do not have to be saved
        (empty list or `None` are accepted)
    """
    
    def wrapper(method):
        def wrapped_method(obj, *args, **kwargs):
            logger.debug('executing transactional method %r', method)
            restore = memento(obj, exclude)
            
            try:
                result = method(obj, *args, **kwargs)
            
            except:
                logger.debug('transaction aborted')
                restore()
                raise
            
            logger.debug('transaction completed')
            return result
        
        return wrapped_method
    return wrapper


# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
