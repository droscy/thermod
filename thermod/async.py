# -*- coding: utf-8 -*-
"""Draft long polling socket

Copyright (C) 2017 Simone Rossetto <simros85@gmail.com>

This file is part of Thermod.

Thermod is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Thermod is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Thermod.  If not, see <http://www.gnu.org/licenses/>.
"""

import time
import logging
import asyncio
import jsonschema

from threading import Thread, Condition
from json.decoder import JSONDecodeError
from aiohttp.web import Application, json_response
from email.utils import formatdate
from datetime import datetime

from . import timetable
from .common import LogStyleAdapter, ThermodStatus
from .memento import memento
from .heating import HeatingError
from .thermometer import ThermometerError
from .version import __version__ as PROGRAM_VERSION

__date__ = '2017-03-19'
__updated__ = '2017-04-04'
__version__ = '0.1'

baselogger = LogStyleAdapter(logging.getLogger(__name__))

REQ_PATH_SETTINGS = ('settings', )
REQ_PATH_HEATING = ('status', 'heating')
REQ_PATH_VERSION = ('version', )
REQ_PATH_TEAPOT = ('elena', 'tea')
REQ_PATH_MONITOR = ('monitor', )

REQ_SETTINGS_ALL = 'settings'
#REQ_SETTINGS_DAYS = 'days'
REQ_SETTINGS_STATUS = timetable.JSON_STATUS
REQ_SETTINGS_T0 = timetable.JSON_T0_STR
REQ_SETTINGS_TMIN = timetable.JSON_TMIN_STR
REQ_SETTINGS_TMAX = timetable.JSON_TMAX_STR
REQ_SETTINGS_DIFFERENTIAL = timetable.JSON_DIFFERENTIAL
REQ_SETTINGS_GRACE_TIME = timetable.JSON_GRACE_TIME

RSP_ERROR = 'error'
RSP_MESSAGE = 'message'
RSP_FULLMSG = 'explain'
RSP_VERSION = 'version'


#async def return_author(request):
#    future = asyncio.Future(loop=request.app.loop)
#    await request.app['q'].put(future)
#    return web.json_response(await asyncio.wait_for(future, timeout=None, loop=request.app.loop))
#
#async def put_author(request):
#    q = request.app['q']
#    p = await request.post()
#    a = p.get('author', 'unknown')
#    print(a)
#    for i in range(q.qsize()):
#        q.get_nowait().set_result({'author': a})
#    return web.Response()
#
#
#loop = asyncio.get_event_loop()
#app = web.Application(loop=loop)
#queue = asyncio.Queue(loop=loop)
#
#app['q'] = queue
#app.router.add_get('/', return_author)
#app.router.add_post('/', put_author)
#web.run_app(app, host='127.0.0.1', port=8080)



### nuovo socket ###

class ClientAddressLogAdapter(logging.LoggerAdapter):
    """Add client address and port to the logged messagges."""
    
    def __init__(self, logger, client_address, extra=None):
        super().__init__(logger, extra)
        self.client_address = client_address
    
    def log(self, level, msg, *args, **kwargs):
        self.logger.log(level, '{} {}'.format(self.client_address, msg), *args, **kwargs)


class ControlSocket(Thread):
    """Start a HTTP server ready to receive commands in a separate thread."""
    
    def __init__(self, timetable, heating, thermometer, host, port, lock, loop):
        baselogger.debug('initializing ControlSocket')
        super().__init__(name='ThermodControlSocket')
        
        # TODO decidere se si deve controllare la classe del lock
        if not isinstance(lock, Condition):
            raise TypeError('the lock in ControlSocket must be a threading.Condition object')
        
        self.app = Application(middlewares=[exceptions_middleware], loop=loop)
        self.host = host
        self.port = port
        
        self.app['lock'] = lock
        self.app['monitors'] = asyncio.Queue(loop=loop)
        
        self.app['timetable'] = timetable
        self.app['heating'] = heating
        self.app['thermometer'] = thermometer
        
        self.app.router.add_get('/{action}', GET_handler)
        self.app.router.add_post('/{action}', POST_handler)
    
    #def __repr__(self):
    #    return '{module}.{cls}({timetable!r}, {host!r}, {port:d})'.format(
    #                module=self.__module__,
    #                cls=self.__class__.__name__,
    #                timetable=self.server.timetable,
    #                host=self.server.server_address[0],
    #                port=self.server.server_address[1])
    
    def run(self):
        #baselogger.info('control socket listening on {}:{}', self.host, self.port)
        #run_app(self.app, host=self.host, port=self.port)
        
        loop = self.app.loop
        loop.run_until_complete(self.app.startup())
        handler = self.app.make_handler()
        
        srv = loop.run_until_complete(loop.create_server(handler, self.host, self.port))
        baselogger.info('control socket listening on {}:{}', self.host, self.port)
        
        try:
            loop.run_forever()
        
        except:
            # TODO gestire le eccezioni
            raise
        
        finally:
            # TODO mettere messaggi di debug
            srv.close()
            loop.run_until_complete(srv.wait_closed())
            loop.run_until_complete(self.app.shutdown())
            loop.run_until_complete(handler.shutdown(6))
            loop.run_until_complete(self.app.cleanup())
        
        loop.close()
        
    
    def stop(self):
        """Stop this control thread shutting down the internal HTTP server."""
        self.app.loop.stop()
        baselogger.info('control socket halted')


def _last_mod_hdr(last_mod_time):
    return {'Last-Modified': formatdate(last_mod_time, usegmt=True)}


async def exceptions_middleware(app, handler):
    """Handle exceptions raised during HTTP requests."""
    
    async def exceptions_handler(request):
        #pippo = request.transport.get_extra_info('peername')
        #print(len(pippo), pippo[0], pippo[1])
        logger = ClientAddressLogAdapter(baselogger, request.transport.get_extra_info('peername'))
        logger.info('received "{} {}" request', request.method, request.url.path)
        
        #if request.method == 'POST':
        #    # Saving timetable state for a manual restore in case of unknown
        #    # errors or in case of errors updating more than one single setting.
        #    restore_old_settings = memento(app['timetable'], exclude=['_lock'])
        
        try:
            response = await handler(request)
        
        #except HTTPError as rsp_err:
        #    # If the handler raised an HTTPError, here we simply send
        #    # it back as response.
        #    logger.debug('responding with an HTTPError created by the request handler')
        #    response = rsp_err
        
        except JSONDecodeError as jde:
            logger.warning('cannot update settings, the {} request contains '
                           'invalid JSON syntax: {}', request.method, jde)
            
            message = 'Invalid JSON syntax'
            response = json_response(status=400,
                                     reason=message,
                                     data={RSP_ERROR: message,
                                           RSP_FULLMSG: '{}: {}'.format(message, jde)})
        
        except jsonschema.ValidationError as jsve:
            logger.warning('cannot update settings, the {} request contains '
                           'incomplete or invalid data in JSON element {}: {}',
                            request.method,
                            list(jsve.path),
                            jsve.message)
            
            message = 'Incomplete or invalid JSON element'
            response = json_response(status=400,
                                     reason=message,
                                     data={RSP_ERROR: message,
                                           RSP_FULLMSG: '{} {}: {}'
                                                        .format(message,
                                                                list(jsve.path),
                                                                jsve.message)})
        
        except ValueError as ve:
            logger.warning('cannot update settings, the {} request contains '
                           'incomplete or invalid data: {}', request.method, ve)
            
            message = 'Incomplete or invalid settings'
            response = json_response(status=400,
                                     reason=message,
                                     data={RSP_ERROR: message,
                                           RSP_FULLMSG: '{}: {}'.format(message, ve)})
        
        except IOError as ioe:
            # Can be raised only by timetable.save() method, so the
            # internal settings have already been updated but cannot
            # be saved to filesystem, so in case of daemon restart
            # they will be lost.
            
            logger.error('cannot save new settings to fileystem: {}', ioe)
            message = 'Cannot save new settings to fileystem'
            response = json_response(
                    status=503,
                    reason=message,
                    data={RSP_ERROR: message,
                          RSP_FULLMSG: ('new settings accepted and '
                                        'applied on running Thermod but they '
                                        'cannot be saved to filesystem so, on '
                                        'daemon restart, they will be lost, '
                                        'try again in a couple of minutes')})
        
        except HeatingError as he:
            message = 'Heating Error'
            logger.warning('{}: {}', message.lower(), he)
            response = json_response(status=503,
                                     reason=message,
                                     data={RSP_ERROR: message, RSP_FULLMSG: str(he)})
        
        except ThermometerError as te:
            message = 'Thermometer Error'
            logger.warning('{}: {}', message.lower(), te)
            response = json_response(status=503,
                                     reason=message,
                                     data={RSP_ERROR: message, RSP_FULLMSG: str(te)})
        
        # TODO gestire anche CancelledError
        except Exception as e:
            # this is an unhandled exception, a critical message is printed
            if request.method == 'POST':
                logger.critical('cannot update settings, the POST request '
                                'produced an unhandled {} exception',
                                type(e).__name__, exc_info=True)
                
                # We execute a manual restore of the old settings to be
                # sure to leave the timetable in a valid state.
                #restore_old_settings()
            
            else:
                logger.critical('the {} request produced an unhandled '
                                '{} exception', request.method,
                                                type(e).__name__,
                                                exc_info=True)
            
            message = 'Cannot process the request'
            response = json_response(status=500,
                                     reason=message,
                                     data={RSP_ERROR: message,
                                           RSP_FULLMSG: '{}: {}'.format(message, e)})
        
        finally:
            logger.debug('sending back response')
        
        return response
    
    return exceptions_handler


async def GET_handler(request):
    logger = ClientAddressLogAdapter(baselogger, request.transport.get_extra_info('peername'))
    logger.debug('processing "{} {}" request', request.method, request.url.path)
    
    lock = request.app['lock']
    timetable = request.app['timetable']
    heating = request.app['heating']
    thermometer = request.app['thermometer']
    
    action = request.match_info['action']
    
    if action in REQ_PATH_VERSION:
        logger.debug('preparing response with Thermod version')
        response = json_response(status=200, data={RSP_VERSION: PROGRAM_VERSION})
    
    elif action in REQ_PATH_SETTINGS:
        logger.debug('preparing response with Thermod settings')
        
        with lock:
            settings = timetable.settings()
            last_updt = timetable.last_update_timestamp()
        
        response = json_response(status=200,
                                 headers=_last_mod_hdr(last_updt),
                                 text=settings)
    
    elif action in REQ_PATH_HEATING:
        logger.debug('preparing response with Thermod current status')
        
        with lock:
            last_updt = time.time()
            status = ThermodStatus(last_updt,
                                   timetable.status,
                                   heating.status,
                                   thermometer.temperature,
                                   timetable.target_temperature(last_updt))
        
        response = json_response(status=200,
                                 headers=_last_mod_hdr(last_updt),
                                 data=status._asdict())
    
    elif action in REQ_PATH_TEAPOT:
        message = 'I\'m a teapot'
        logger.info(message)
        response = json_response(
            status=418,
            reason=message,
            headers=_last_mod_hdr(datetime(2017, 7, 29, 17, 0).timestamp()),
            data={RSP_ERROR: 'To my future wife',
                  RSP_FULLMSG: ('I dedicate this application to Elena, '
                                'my future wife.')})
    
    elif action in REQ_PATH_MONITOR:
        logger.debug('enqueuing new long-polling monitor request')
        future = asyncio.Future(loop=request.app.loop)
        await request.app['monitors'].put(future)
        
        logger.debug('waiting for timetable status change')
        status = await asyncio.wait_for(future, timeout=None, loop=request.app.loop)
        
        logger.debug('preparing response with monitor update')
        response = json_response(status=200,
                                 headers=_last_mod_hdr(status.timestamp),
                                 data=status._asdict())
    
    else:
        message = 'Invalid Request'
        logger.warning('{} "{} {}" received', message.lower(), request.method, request.url.path)
        response = json_response(status=404, reason=message, data={RSP_ERROR: message})
    
    logger.debug('response ready')
    return response


async def POST_handler(request):
    logger = ClientAddressLogAdapter(baselogger, request.transport.get_extra_info('peername'))
    logger.debug('processing "{} {}" request', request.method, request.url.path)
    
    lock = request.app['lock']
    timetable = request.app['timetable']
    action = request.match_info['action']
    
    if action in REQ_PATH_SETTINGS:
        logger.debug('parsing received POST data')
        postvars = await request.post()
        logger.debug('POST variables: {}', postvars)
        
        with lock:
            # Saving timetable state for a manual restore in case of
            # errors during saving to filesystem or in case of errors
            # updating more than one single setting.
            restore_old_settings = memento(timetable)
            
            # updating all settings
            if REQ_SETTINGS_ALL in postvars:
                logger.debug('updating Thermod settings')
                
                try:
                    timetable.load(postvars[REQ_SETTINGS_ALL])
                    timetable.save()  # saving changes to filesystem
                
                except (JSONDecodeError, jsonschema.ValidationError):
                    # No additional operation required, re-raise for default handling.
                    raise
                
                except IOError:
                    # Some settings of timetable could have been updated,
                    # we notify this changes in order to check again the
                    # current temperature.
                    
                    lock.notify_all()
                    raise
                
                except Exception:
                    # This is an unhandled exception, so we execute a
                    # manual restore of the old settings to be sure to
                    # leave the timetable in a valid state, then we
                    # re-raise the exception for default handling.
                    
                    restore_old_settings()
                    raise
                
                message = 'all settings updated'
                logger.info(message)
                response = json_response(status=200, data={RSP_MESSAGE: message})
            
            # updating single settings
            elif postvars:
                logger.debug('updating one or more settings')
                
                newvalues = {}
                try:
                    for var, value in postvars.items():
                        if var == REQ_SETTINGS_STATUS:
                            timetable.status = value
                            newvalues[var] = timetable.status
                        elif var == REQ_SETTINGS_T0:
                            timetable.t0 = value
                            newvalues[var] = timetable.t0
                        elif var == REQ_SETTINGS_TMIN:
                            timetable.tmin = value
                            newvalues[var] = timetable.tmin
                        elif var == REQ_SETTINGS_TMAX:
                            timetable.tmax = value
                            newvalues[var] = timetable.tmax
                        elif var == REQ_SETTINGS_DIFFERENTIAL:
                            timetable.differential = value
                            newvalues[var] = timetable.differential
                        elif var == REQ_SETTINGS_GRACE_TIME:
                            timetable.grace_time = value
                            newvalues[var] = timetable.grace_time
                        else:
                            logger.debug('invalid field `{}` ignored', var)
                    
                    # if no settings found in request body rise an error
                    if len(newvalues) == 0:
                        raise jsonschema.ValidationError(
                                'no valid fields found in request body',
                                ('any settings',))
                    
                    # saving changes to filesystem
                    timetable.save()
                
                except jsonschema.ValidationError as jsve:
                    # This exception can be raised after having successfully
                    # updated at least one settings, so any setting must
                    # be manually restored to the old state.
                    
                    logger.warning('cannot update {}: {}', list(jsve.path), jsve.message)
                    
                    message = 'Cannot update settings'
                    response = json_response(
                                    status=400,
                                    reason=message,
                                    data={RSP_ERROR: message,
                                          RSP_FULLMSG: 'Cannot update {}: {}'
                                                       .format(list(jsve.path),
                                                               jsve.message)})
                    
                    # restoring old settings from memento
                    restore_old_settings()
                
                except ValueError as ve:
                    # This exception can be raised after having successfully
                    # updated at least one settings, so any setting must
                    # be manually restored to the old state.
                    
                    logger.warning('cannot update {}: {}', var, ve)
                    
                    message = 'Cannot update settings'
                    response = json_response(
                                    status=400,
                                    reason=message,
                                    data={RSP_ERROR: message,
                                          RSP_FULLMSG: 'Cannot update {}: {}'
                                                        .format(var, ve)})
                    
                    # restoring old settings from memento
                    restore_old_settings()
                
                except IOError:
                    # Some settings of timetable could have been updated,
                    # we notify this changes in order to immediately check
                    # the current temperature.
                    
                    lock.notify_all()
                    raise
                
                except Exception:
                    # This is an unhandled exception, so we execute a
                    # manual restore of the old settings to be sure to
                    # leave the timetable in a valid state, then we
                    # re-raise the exception for default handling.
                    
                    restore_old_settings()
                    raise
                
                message = 'Settings updated'
                logger.info('{}: {}', message.lower(), newvalues)
                response = json_response(status=200, data={RSP_MESSAGE: '{}: {}'.format(message, newvalues)})
            
            else:  # No restore required here because no settings updated
                logger.warning('cannot update settings, the POST request is empty')
                
                message = 'No settings provided'
                response = json_response(status=400,
                                         reason=message,
                                         data={RSP_ERROR: message})
            
            # If some settings of timetable have been updated, we'll notify
            # this changes in order to recheck current temperature.
            if response.status == 200:
                lock.notify_all()
    
    else:
        message = 'Invalid Request'
        logger.warning('{} "{} {}" received', message.lower(), request.method, request.url.path)
        response = json_response(status=404, reason=message, data={RSP_ERROR: message})
    
    return response

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab
