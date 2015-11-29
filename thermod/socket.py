"""Control socket to manage thermod from external applications."""

import sys
import logging
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

from . import config
from .timetable import TimeTable

__updated__ = '2015-11-29'
__version__ = '0.1'

logger = logging.getLogger((__name__ == '__main__' and 'thermod') or __name__)

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
    
    def send_head(self):
        """Send the full response header and return the JSON settings.
        
        If the HTTP request is valid, this method returns the whole settings
        as JSON-encoded string that can be sent back to the client, otherwise
        `None` is returned along with a 404 error.
        """
        
        settings = None
        
        if self.path == '/settings':
            logger.info('{} sending back Thermod settings'
                        .format(self.client_address))
            
            with self.server.timetable.lock:
                settings = self.server.timetable.settings().encode('utf-8')
                size = len(settings)
                last_updt = self.server.timetable.last_update_timestamp()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header("Content-Length", size)
            self.send_header("Last-Modified", self.date_time_string(last_updt))
            self.end_headers()
        
        else:
            logger.warning('{} invalid request received, '
                           'sending back 404 error'.format(self.client_address))
            
            self.send_error(404, 'the requested object cannot be found')
        
        return settings
    
    
    def do_HEAD(self):
        """Send the HTTP header."""
        
        logger.info('{} received "{} {}" command'
                    .format(self.client_address, self.command, self.path))
        
        self.send_head()
        
        logger.info('{} header sent, connection closed'.format(self.client_address))
    
    
    def do_GET(self):
        """Manage the GET request sending back the whole settings."""
        
        logger.info('{} received "{} {}" command'
                    .format(self.client_address, self.command, self.path))
        
        settings = self.send_head()
        
        if settings:
            self.wfile.write(settings)
        
        logger.info('{} response sent, connection closed'.format(self.client_address))
    
    
    def do_POST(self):
        # TODO this method
        pass


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
