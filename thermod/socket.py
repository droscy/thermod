"""Control socket to manage thermod from external applications.

The following is the schema of commands: TODO
"""

import logging
import json
import jsonschema
import socket
import struct
from base64 import b64decode
from threading import Thread, Event

from . import TimeTable, config
from .jsocket import ServerFactoryThread

# TODO Il jsocket nativo non funziona, ho importato qui tutto il codice
# ma devo farmi il mio socket dato che più o meno ho capito come funzionano
# i socket
#
# j = json.dumps(obj).encode('utf-8')
# size = len(j)
# hdr = struct.pack('!I',size)
# msg= struct.pack('!{}s'.format(size),j)


__updated__ = '2015-11-18'


logger = logging.getLogger(__name__)

# If the msg_schema changes, also the following variables must be
# changed accordingly
msg_schema = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'title': 'Socket Messages',
    'description': 'Thermod socket messages (JSON encoded)',
    'type': 'object',
    'properties': {
        'action': {'enum': ['GET' ,'SET', 'ACK', 'RSP', 'ERR']},
        'settings': {'type': 'array', 'items': {'enum': ['day']}},
        'day_name': {'enum': list(set(config.json_days_name_map.values()))},
        'day_data': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]}},
    'required': ['action'],
    'additionalProperties': True,  # additional properties are values of SET action
    'definitions': {'day': config.json_schema['definitions']['day']}
}

msg_schema['properties']['settings']['items']['enum'].extend(list(config.json_schema['properties'].keys()))
msg_schema['properties'].update(config.json_schema['properties'])

msg_action = 'action'
msg_action_get = 'GET'
msg_action_set = 'SET'
msg_action_ack = 'ACK'
msg_action_rsp = 'RSP'
msg_action_err = 'ERR'

msg_settings = 'settings'
msg_settings_status = config.json_status
msg_settings_differential = config.json_differential
msg_settings_grace_time = config.json_grace_time
msg_settings_temperatures = config.json_temperatures
msg_settings_timetable = config.json_timetable
msg_settings_day = 'day'
msg_settings_day_name = 'day_name'
msg_settings_day_data = 'day_data'


class ControlThread(Thread):
    def __init__(self, timetable, address='127.0.0.1', port=4344):
        super(ControlThread,self).__init__()
        
        if not isinstance(timetable, TimeTable):
            raise TypeError('ControlThread requires a TimeTable object')
        
        self._timetable = timetable
        
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind((address, port))
        self._server_socket.listen(5)
        self._server_socket.settimeout(30)
        
        self._stop = Event()
        self._clients = []
    
    def run(self):
        # TODO fare questo metodo, deve rimanere in attesa finché dall'esterno
        # non si decide di interromperlo, nella sua attività resta in ascolto
        # e istanzia il client socket che poi deve avviarsi con un thread
        # separato e processare il messaggio
        #Thread.run(self)
        
        while not self._stop.is_set():
            # TODO gestire le eccezioni
            (client, address) = self._server_socket.accept()
            logger.info('connection to control channel received from '
                        'address {}'.format(address))
            
            cs = ControlSocket(self._timetable, client, address)
            cs.run()
            
            self._clients.append(cs)
        
        # TODO se non ci sono state eccezioni si attende la fine dei processi
        # client, anche se forse potrebbe valer la pena inviare un segnale
        # di chiusura a tutti
        for client in self._clients:
            client.join()
        
        pass
        

class ControlSocket(Thread):
    def __init__(self, timetable, client, address):
        super(ControlThread,self).__init__()
        
        if not isinstance(timetable, TimeTable):
            raise TypeError('ControlSocket requires a TimeTable object as timetable')
        
        if not isinstance(client, socket.socket):
            raise TypeError('ControlSocket requires a socket object as client')
        
        self._timetable = timetable
        self._client_socket = client
        self._address = address
    
    def run(self):
        # TODO gestire eccezioni
        logger.debug('[client {}] connected'.format(self._address))
        
        s = self._client_socket.read(4)
        size = struct.unpack('!I', s)
        logger.debug('[client {}] received message size: {} bytes'.format(self._address, size))
        
        data = b''
        while len(data) < size:
            tmp_data = self.conn.recv(min(4096,size-len(data)))
            
            if tmp_data == '':
                logger.debug('[client {}] socket connection broken'.format(self._address))
                raise RuntimeError('socket connection broken from client {}'.format(self._address))
            
            data += tmp_data
        
        logger.debug('[client {}] received message data'.format(self._address))
        
        # TODO se non ci sono state eccezioni si recupera il messaggio
        msg = json.loads(struct.unpack('!{}s'.format(size),data).decode('utf-8'))
        
        try:
            jsonschema.validate(msg, msg_schema)
            
            tt = self._timetable
            with tt._TimeTable__lock: # TODO il nome dell'attributo __lock deve essere modificato
                
                if msg[msg_action] == msg_action_set:
                    for setting in msg[msg_settings]:
                        if setting == msg_settings_status:
                            tt.status = msg[msg_settings_status]
                        elif setting == msg_settings_differential:
                            tt.differential = msg[msg_settings_differential]
                        elif setting == msg_settings_grace_time:
                            tt.grace_time = msg[msg_settings_grace_time]
                        elif setting == msg_settings_temperatures:
                            tt.t0 = msg[msg_settings_temperatures][config.json_t0_str]
                            tt.tmin = msg[msg_settings_temperatures][config.json_tmin_str]
                            tt.tmax = msg[msg_settings_temperatures][config.json_tmax_str]
                        elif setting == msg[msg_settings_day]:
                            day = msg[msg_settings_day_name]
                            data = msg[msg_settings_day_data]
                            
                            #for hour in range(24):
                            #    for quarter in range(4):
                            #        temperature = data[config.json_format_hour(hour)][quarter]
                            #        tt.update(day,hour,quarter,temperature)
                            
                            # TODO si deve creare il metodo day() in TimeTable per aggiornare un giorno intero
                
                # TODO finire questo metodo
                
        except jsonschema.ValidationError as e:
            # TODO
            pass




class OldControlSocket(ServerFactoryThread):
    """Socket factory that receives commands from external clients."""
    
    def __init__(self, timetable):
        super(OldControlSocket, self).__init__()
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
            
            if obj[msg_settings] in obj:
                pass
            else:
                logger.warning('missing the new value for setting "{}"'.format(obj[msg_settings]))
        else:
            logger.info('processing GET message for setting "{}"'.format(obj[msg_settings]))
            # TODO deve essere creata la parte di invio del messaggio di risposta
            pass
        
        pass
