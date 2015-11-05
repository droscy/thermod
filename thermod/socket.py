"""Control socket to manage thermod from external applications.

The following is the schema of commands: TODO
"""

import logging
import jsonschema
from base64 import b64decode
from jsocket import ServerFactoryThread
from thermod import TimeTable

__updated__ = '2015-11-05'


logger = logging.getLogger(__name__)

# If the msg_schema changes, also the following variables must be
# changed accordingly
msg_schema = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'title': 'Socket Messages',
    'description': 'Thermod socket messages (JSON encoded)',
    'type': 'object',
    'properties': {
        'action': {'enum': ['GET' ,'SET']},
        'settings': {'type': 'array',
                     'items': {'enum': ['status', 'differential', 'grace_time',
                                        'temperatures', 'timetable', 'days']}}},
    'required': ['action', 'settings'],
    'additionalProperties': True  # additional properties are values of SET action
}

msg_action = 'action'
msg_action_set = 'SET'
msg_action_get = 'GET'

msg_object = 'settings'
msg_object_status = 'status'
msg_object_diff = 'differential'
msg_object_grace = 'grace_time'
msg_object_temperatures = 'temperatures'
msg_object_timetable = 'timetable'
msg_object_days = 'days'


class ControlSocket(ServerFactoryThread):
    """Socket factory that receives commands from external clients."""
    
    def __init__(self, timetable):
        super(ControlSocket, self).__init__()
        self.timeout = None
        
        if not isinstance(timetable, TimeTable):
            logger.debug('ControlSocket requires a TimeTable object')
            raise TypeError('ControlSocket requires a TimeTable object')
        
        self._timetable = timetable
    
    
    def _process_message(self, obj):
        logger.info('message received')
        logger.debug(obj)
        
        try:
            jsonschema.validate(obj, msg_schema)
            logger.debug('the message is valid')
        except:
            # TODO il messaggio non è valido
            return
        
        if obj[msg_action] == msg_action_set:
            # TODO gestire array di messaggi
            logger.info('processing SET message')
            
            if obj[msg_object] in obj:
                pass
            else:
                logger.warning('missing the new value for setting "{}"'.format(obj[msg_object]))
        else:
            logger.info('processing GET message for setting "{}"'.format(obj[msg_object]))
            # TODO deve essere creata la parte di invio del messaggio di risposta
            pass
        
        pass
