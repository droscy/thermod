"""Control socket to manage thermod from external applications."""

import cgi
import sys
import json
import logging
import time
from jsonschema import ValidationError
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

from . import config
from .timetable import TimeTable
from .config import JsonValueError

# TODO aggiungere modo per aggiornare l'orario di un singolo giorno
# TODO write test cases for thermod.socket

__updated__ = '2015-12-05'
__version__ = '0.1'

logger = logging.getLogger((__name__ == '__main__' and 'thermod') or __name__)


req_settings_all = 'settings'
#req_settings_day = 'day'
req_settings_status = config.json_status
req_settings_t0 = config.json_t0_str
req_settings_tmin = config.json_tmin_str
req_settings_tmax = config.json_tmax_str
req_settings_differential = config.json_differential
req_settings_grace_time = config.json_grace_time

req_settings_paths = ('/settings', '/settings/')

rsp_error = 'error'
rsp_message = 'message'
rsp_fullmsg = 'explain'


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
    
    def _send_header(self, code, message=None, json_data=None, last_modified=None):
        self.send_response_only(code, message)
        
        if json_data:
            self.send_header('Content-Type', 'application/json;charset=utf-8')
            self.send_header('Content-Length', len(json_data))
            self.send_header('Last-Modified',
                             self.date_time_string(last_modified or time.time()))
        
        self.send_header('Connection', 'close')
        self.send_header('Server', self.version_string())
        self.send_header('Date', self.date_time_string())
    
    def do_HEAD(self):
        """Send the HTTP header equal to the one of the GET request."""
        
        logger.info('{} received "{} {}" command'
                    .format(self.client_address, self.command, self.path))
        
        data = None
        
        if self.stripped_lowered_path in req_settings_paths:
            logger.info('{} sending back Thermod settings'.format(self.client_address))
            
            with self.server.timetable.lock:
                data = self.server.timetable.settings.encode('utf-8')
                last_updt = self.server.timetable.last_update_timestamp()
            
            self._send_header(200, json_data=data, last_modified=last_updt)
            
        else:
            error = 404
            logger.warning('{} invalid request path, sending back error '
                           'code {:d}'.format(self.client_address, error))
            
            message = 'path not found'
            data = json.dumps({rsp_error: message}).encode('utf-8')
            self._send_header(404, message, data)
        
        self.end_headers()
        logger.info('{} header sent'.format(self.client_address))
        
        return data
    
    def do_GET(self):
        """Manage the GET request sending back all settings as JSON string."""
        
        settings = self.do_HEAD()
        
        if settings:
            self.wfile.write(settings)
            logger.info('{} response sent'.format(self.client_address))
        
        logger.info('{} closing connection'.format(self.client_address))
    
    def do_POST(self):
        """Manage the POST request updating timetable settings.
        
        With this request a client can update the settings of the daemon. The
        request path is the same of the GET method and the new settings must
        be present in the body of the request.
        
        Accepted settings in the body:
            * `settings` to update the whole state (JSON encoded settings)
            * TODO the other values
        """
        # TODO completare la documentazione con la descrizione dei campi accettati
        
        logger.info('{} received "{} {}" command'
                    .format(self.client_address, self.command, self.path))
        
        code = None
        data = None
        
        if self.stripped_lowered_path in req_settings_paths:
            logger.debug('{} parsing received POST data'.format(self.client_address))
            
            # code copied from http://stackoverflow.com/a/13330449
            ctype, pdict = cgi.parse_header(self.headers['Content-Type'])
            
            if ctype == 'multipart/form-data':
                postvars = cgi.parse_multipart(self.rfile, pdict)
            elif ctype == 'application/x-www-form-urlencoded':
                length = int(self.headers['Content-Length'])
                postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
            else:
                postvars = {}
            
            # TODO capire se questo aggiustamento serve sempre
            postvars = {k.decode('utf-8'): v[0].decode('utf-8') for k,v in postvars.items()}
            
            logger.debug('{} POST content-type: {}'.format(self.client_address, ctype))
            logger.debug('{} POST variables: {}'.format(self.client_address, postvars))
            
            if req_settings_all in postvars:
                with self.server.timetable.lock:
                    logger.info('{} updating Thermod settings'.format(self.client_address))
                    
                    try:
                        self.server.timetable.settings = postvars[req_settings_all]
                        self.server.timetable.save()  # saving changes to filesystem
                    
                    except ValidationError as ve:
                        code = 400
                        
                        logger.warning('{} cannot update settings, the POST '
                                       'request contains incomplete or invalid '
                                       'data: {}'.format(self.client_address,
                                                         ve.message))
                        
                        message = 'incomplete or invalid JSON-encoded settings'
                        response = {rsp_error: message, rsp_fullmsg: ve.message}
                    
                    except IOError as ioe:
                        # can be raised only by timetable.save() method, so the
                        # internal settings have already been updated and a
                        # reload of the old settings is required
                        code = 500
                        logger.critical('{} cannot save new settings to '
                            'fileystem: {}'.format(self.client_address, ioe))
                        
                        message = 'cannot save new settings to filesystem'
                        response = {rsp_error: message, rsp_fullmsg: str(ioe)}
                        
                        # reloading old settings still present on filesystem
                        self.server.timetable.reload()
                    
                    except Exception as e:
                        code = 500
                        
                        logger.critical('{} Cannot update settings, the POST '
                                        'request produced an unhandled '
                                        'exception; in order to diagnose what '
                                        'happened execute Thermod in debug '
                                        'mode and resubmit the last request.'
                                        .format(self.client_address))
                        
                        logger.debug('{} {}: {}'.format(self.client_address,
                                                        type(e).__name__, e))
                        
                        message = 'cannot process the request'
                        response = {rsp_error: message, rsp_fullmsg: str(e)}
                        
                        # reloading old settings still present on filesystem
                        self.server.timetable.reload()
                    
                    else:
                        code = 200
                        message = 'settings updated'
                        logger.info('{} {}'.format(self.client_address, message))
                        response = {rsp_message: message}
                    
                    finally:
                        data = json.dumps(response).encode('utf-8')
                        self._send_header(code, message, data)
            
            elif postvars:
                with self.server.timetable.lock:
                    try:
                        for var, value in postvars.items():
                            if var == req_settings_status:
                                self.server.timetable.status = value
                            elif var == req_settings_t0:
                                self.server.timetable.t0 = value
                            elif var == req_settings_tmin:
                                self.server.timetable.tmin = value
                            elif var == req_settings_tmax:
                                self.server.timetable.tmax = value
                            elif var == req_settings_differential:
                                self.server.timetable.differential = value
                            elif var == req_settings_grace_time:
                                self.server.timetable.grace_time = value
                            else:
                                raise ValidationError('invalid variable `{}` '
                                                      'in request body'
                                                      .format(var))
                        
                        # saving changes to filesystem
                        self.server.timetable.save()
                    
                    except ValidationError as ve:
                        code = 400
                        logger.warning('{} cannot update settings: {}'
                                       .format(self.client_address, ve.message))
                        
                        message = 'cannot update settings'
                        response = {rsp_error: message, rsp_fullmsg: ve.message}
                        
                        # reloading old settings still present on filesystem
                        self.server.timetable.reload()
                    
                    except JsonValueError as jve:
                        code = 400
                        logger.warning('{} cannot update {}: {}'
                                       .format(self.client_address, var, jve))
                        
                        message = 'cannot update settings'
                        response = {rsp_error: message, rsp_fullmsg: str(jve)}
                        
                        # reloading old settings still present on filesystem
                        self.server.timetable.reload()
                    
                    except IOError as ioe:
                        # can be raised only by timetable.save() method, so the
                        # internal settings have already been updated and a
                        # reload of the old settings is required
                        code = 500
                        logger.critical('{} cannot save new settings to '
                            'fileystem: {}'.format(self.client_address, ioe))
                        
                        message = 'cannot save new settings to filesystem'
                        response = {rsp_error: message, rsp_fullmsg: str(ioe)}
                        
                        # reloading old settings still present on filesystem
                        self.server.timetable.reload()
                    
                    except Exception as e:
                        code = 500
                        
                        logger.critical('{} Cannot update settings, the POST '
                                        'request produced an unhandled '
                                        'exception; in order to diagnose what '
                                        'happened execute Thermod in debug '
                                        'mode and resubmit the last request.'
                                        .format(self.client_address))
                        
                        logger.debug('{} {}: {}'.format(self.client_address,
                                                        type(e).__name__, e))
                        
                        message = 'cannot process the request'
                        response = {rsp_error: message, rsp_fullmsg: str(e)}
                        
                        # reloading old settings still present on filesystem
                        self.server.timetable.reload()
                    
                    else:
                        code = 200
                        message = 'settings {} updated'.format(list(postvars.keys()))
                        logger.info('{} {}'.format(self.client_address, message))
                        response = {rsp_message: message}
                    
                    finally:
                        data = json.dumps(response).encode('utf-8')
                        self._send_header(code, message, data)
            
            else:
                code = 400
                logger.warning('{} cannot update settings, the POST request '
                               'contains no data'.format(self.client_address))
                
                message = 'no settings provided'
                data = json.dumps({rsp_error: message}).encode('utf-8')
                self._send_header(code, message, data)
        
        else:
            code = 404
            logger.warning('{} invalid request path'.format(self.client_address))
            
            message = 'path not found'
            data = json.dumps({rsp_error: message}).encode('utf-8')
            self._send_header(404, message, data)
        
        logger.info('{} sending back {} code {:d}'
                    .format(self.client_address,
                            ((code>=400) and 'error' or 'status'),
                            code))
        
        self.end_headers()
        logger.debug('{} header sent'.format(self.client_address))
        
        if data:
            self.wfile.write(data)
            logger.info('{} response sent'.format(self.client_address))
        
        logger.info('{} closing connection'.format(self.client_address))


# only for debug purpose
if __name__ == '__main__':
    import os
    import shutil
    import tempfile
    
    logger.setLevel(logging.DEBUG)
    
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(fmt=config.logger_fmt_msg,
                                           datefmt=config.logger_fmt_date))
    logger.addHandler(console)
    
    file = 'timetable.json'
    tmpfile = os.path.join(tempfile.gettempdir(),file)
    shutil.copy(file, tmpfile)
    tt = TimeTable(tmpfile)
    cc = ControlThread(tt)
    
    try:
        cc.start()
        cc.join()
    except:
        cc.server.shutdown()
        logger.info('control server stopped')
