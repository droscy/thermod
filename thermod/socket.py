"""Control socket to manage thermod from external applications."""

import cgi
import sys
import logging
from jsonschema import ValidationError
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

from . import config
from .timetable import TimeTable


__updated__ = '2015-12-03'
__version__ = '0.1'

logger = logging.getLogger((__name__ == '__main__' and 'thermod') or __name__)

req_settings_paths = ('/settings', '/settings/')

# TODO finire i vari messaggi
req_settings_all = 'settings'
#req_settings_day = 'day'
#req_settings_status = config.json_status
#req_settings_t0 = config.json_t0_str
#req_settings_tmin = config.json_tmin_str
#req_settings_tmax = config.json_tmax_str

rsp_error = 'error'
rsp_shortmsg = 'shortmsg'
rsp_fullmsg = 'fullmsg'


# TODO write test cases for thermod.socket


class ControlThread(Thread):
    """Start a HTTP server ready to receive commands."""
    
    def __init__(self, timetable, host='localhost', port=4344):
        super().__init__()
        
        if not isinstance(timetable, TimeTable):
            raise TypeError('ControlThread requires a TimeTable object')
        
        self.server = ControlServer(timetable, (host, port), ControlRequestHandler)
    
    def run(self):
        (host, port) = self.server.server_address
        logger.info('control server listening on {}:{}'.format(host, port))
        self.server.serve_forever()


class ControlServer(HTTPServer):
    """Receive HTTP connections and dispatch a reequest handler."""
    
    def __init__(self, timetable, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        
        if not isinstance(timetable, TimeTable):
            raise TypeError('ControlServer requires a TimeTable object')
        
        self.timetable = timetable
        logger.debug('ControlServer initialized on {}'.format(self.server_address))
    
    def shutdown(self):
        logger.debug('shutting down ControlServer {}'.format(self.server_address))
        super().shutdown()


class ControlRequestHandler(BaseHTTPRequestHandler):
    """Receive and manages control commands."""
    
    BaseHTTPRequestHandler.server_version = 'Thermod/{}'.format(__version__)
    
    @property
    def stripped_lowered_path(self):
        """Strip arguments from path and lower the result."""
        idx = self.path.find('?')
        
        if idx >= 0:
            rpath = self.path[:idx]
        else:
            rpath = self.path
        
        return rpath.lower()
    
    def do_HEAD(self):
        """Send the HTTP header."""
        
        logger.info('{} received "{} {}" command'
                    .format(self.client_address, self.command, self.path))
        
        settings = None
        
        if self.stripped_lowered_path in req_settings_paths:
            logger.info('{} sending back Thermod settings'.format(self.client_address))
            
            with self.server.timetable.lock:
                settings = self.server.timetable.settings.encode('utf-8')
                last_updt = self.server.timetable.last_update_timestamp()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(settings))
            self.send_header('Last-Modified', self.date_time_string(last_updt))
        else:
            logger.warning('{} invalid request, sending back error code 404'
                           .format(self.client_address))
            
            self.send_error(404, 'the requested object cannot be found')
        
        self.end_headers()
        logger.info('{} header sent'.format(self.client_address))
        
        return settings
    
    def do_GET(self):
        """Manage the GET request sending back the whole settings."""
        
        settings = self.do_HEAD()
        
        if settings:
            self.wfile.write(settings)
            logger.info('{} response sent'.format(self.client_address))
        
        logger.info('{} closing connection'.format(self.client_address))
    
    def do_POST(self):
        """Manage the POST request updating timetable settings."""
        
        logger.info('{} received "{} {}" command'
                    .format(self.client_address, self.command, self.path))
        
        if self.stripped_lowered_path in req_settings_paths:
            logger.debug('{} parsing received POST data'.format(self.client_address))
            
            # code copied from http://stackoverflow.com/a/4233452
            ctype, pdict = cgi.parse_header(self.headers.getheader('Content-Type'))
            
            if ctype == 'multipart/form-data':
                postvars = cgi.parse_multipart(self.rfile, pdict)
            elif ctype == 'application/x-www-form-urlencoded':
                length = int(self.headers.getheader('Content-Length'))
                postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
            else:
                postvars = {}
            
            logger.debug('{} POST content-type: {}'.format(self.client_address, ctype))
            logger.debug('{} POST variables: {}'.format(self.client_address, postvars))
            
            response = {rsp_error: False, rsp_shortmsg: '', rsp_fullmsg: ''}
            
            if req_settings_all in postvars:
                with self.server.timetable.lock:
                    logger.info('{} updating Thermod settings'.format(self.client_address))
                    
                    try:
                        self.server.timetable.settings = postvars[req_settings_all]
                        logger.info('{} settings updated'.format(self.client_address))
                        
                        response[rsp_shortmsg] = 'settings updated'
                        self.send_response(200, response[rsp_shortmsg])
                    
                    except ValidationError as ve:
                        error = 400
                        
                        logger.warning(ve.message)  # TODO maybe a debug message
                        logger.warning('{} cannot update settings, the POST '
                                       'request contains incomplete or invalid '
                                       'data, sending back error code {:d}'
                                       .format(self.client_address, error))
                        
                        response[rsp_error] = True
                        response[rsp_shortmsg] = 'incomplete or invalid JSON-encoded settings'
                        response[rsp_fullmsg] = ve.message
                        
                        self.send_error(error, response[rsp_shortmsg])
                        
                    except Exception as e:
                        error = 500
                        
                        logger.critical(e)   # TODO maybe a debug message
                        logger.critical('{} cannot update settings, the POST '
                                        'request produced an unhandled '
                                        'exception; in order to diagnose what '
                                        'happened execute Thermod in debug '
                                        'mode and resubmit the last request; '
                                        'sending back error code {:d}'
                                        .format(self.client_address, error))
                        
                        response[rsp_error] = True
                        response[rsp_shortmsg] = 'cannot process the request'
                        response[rsp_fullmsg] = str(e)
                        
                        self.send_error(error, response[rsp_shortmsg])
                
                # TODO controllare metodo
            
            else:
                # TODO
                pass
                

        else:
            logger.warning('{} invalid request, sending back error code 404'
                           .format(self.client_address))
            # TODO segnare errore nella risposta
            self.send_error(404, 'the requested object cannot be found')
        
        self.end_headers()
        
        # TODO inviare risposta
        #self.wfile.write(json.dumps(response))
        #logger.info('{} response sent'.format(self.client_address))


# only for debug purpose
if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(fmt=config.logger_fmt_msg,
                                           datefmt=config.logger_fmt_date))
    logger.addHandler(console)
    
    tt = TimeTable('timetable.json')
    cc = ControlThread(tt)
    
    try:
        cc.start()
        cc.join()
    except:
        cc.server.shutdown()
        logger.info('control server stopped')
