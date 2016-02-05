#!/usr/bin/env python3

import os
import sys
import logging
import argparse
import signal
import subprocess
import configparser

from daemon import DaemonContext
from configparser import ConfigParser
from logging.handlers import SysLogHandler
from thermod import config
from thermod.heating import ScriptHeating, HeatingError
from thermod.timetable import TimeTable
from thermod.socket import ControlThread
from thermod.config import JsonValueError

# TODO mettere un SMTPHandler per i log di tipo WARNING e CRITICAL
# TODO verificare il corretto spelling di thermod o Thermod in tutti i sorgenti
# TODO documentare return code
# TODO rivedere i messaggi di log, decidere se usare format oppure %s

prog_version = '0.0.0~alpha3'
script_path = os.path.dirname(os.path.realpath(__file__))

# parsing input arguments
parser = argparse.ArgumentParser(description='thermod daemon')
parser.add_argument('-v', '--version', action='version', version='%(prog)s {}'.format(prog_version))
parser.add_argument('-D', '--debug', action='store_true', help='start the daemon in debug mode')
parser.add_argument('-F', '--foreground', action='store_true', help='start the daemon in foreground')
parser.add_argument('-L', '--log', action='store', default=None, help='write messages to log file')
args = parser.parse_args()

# setting up logging system
logger = logging.getLogger(config.logger_base_name)
logger.setLevel(logging.INFO)

if args.debug:
    logger.setLevel(logging.DEBUG)

if args.log:
    # TODO cosa succede se non riesce a scrivere nel log?
    logfile = logging.FileHandler(args.log, mode='w')  # TODO forse mode='a'
    logfile.setFormatter(logging.Formatter(fmt=config.logger_fmt_msg,
                                           datefmt=config.logger_fmt_datetime,
                                           style=config.logger_fmt_style))
    logger.addHandler(logfile)

if args.foreground:
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(fmt=config.logger_fmt_msg,
                                           datefmt=config.logger_fmt_time,
                                           style=config.logger_fmt_style))
    logger.addHandler(console)
    logger.debug('executing in foreground, logging to console')
else:
    syslog = SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_DAEMON)
    syslog.setFormatter(logging.Formatter(fmt=config.logger_fmt_msg_syslog,
                                          style=config.logger_fmt_style))
    logger.addHandler(syslog)
    logger.debug('executing in background, logging to syslog (daemon)')


# reading configuration files
try:
    cfg = ConfigParser()
    cfg.read_string('[global] enabled = 0')  # basic settings to immediatly shutdown if config file is missing
    logger.debug('searching main configuration in files {}'.format(config.main_config_files))
    # TODO mettere un errore se i file mancano
    _cfg_files_found = cfg.read(config.main_config_files) # TODO in caso di più file quale ha precedenza?
    logger.debug('configuration files found: {}'.format(_cfg_files_found))

except configparser.MissingSectionHeaderError as mshe:
    ret_code = 10
    logger.critical('invalid syntax in configuration file `%s`, '
                    'missing sections', mshe.source)

except configparser.ParsingError as pe:
    ret_code = 11
    (_lineno, _line) = pe.errors[0]
    logger.critical('invalid syntax in configuration file `%s` at line %d: %s',
                    pe.source, _lineno, _line)

except configparser.DuplicateSectionError as dse:
    ret_code = 12
    logger.critical('duplicate section `%s` in configuration file `%s`',
                    dse.section, dse.source)

except configparser.DuplicateOptionError as doe:
    ret_code = 13
    logger.critical('duplicate option `%s` in section `%s` of configuration '
                    'file `%s`', doe.option, doe.section, doe.source)

except configparser.Error as cpe:
    ret_code = 14
    logger.critical('unknown error in configuration file: `%s`', cpe)

except Exception as e:
    ret_code = 15
    logger.critical('unknown error in configuration file: `%s`', e)

except:
    ret_code = 15
    logger.critical('unknown error in configuration file, no more details')

else:
    ret_code = 0

finally:
    if ret_code == 0:
        logger.debug('main configuration files read')
    else:
        logger.info('closing daemon with return code {}'.format(ret_code))
        exit(ret_code)

# parsing main settings
try:
    # TODO finire controllo sui valori presenti nel file di config
    enabled = cfg.getboolean('global', 'enabled')
    debug = cfg.getboolean('global', 'debug') or args.debug
    tt_file = cfg.get('global', 'timetable')
    interval = cfg.getint('global', 'interval')
    
    scripts = {'tsensor': cfg.get('scripts', 'sensor'),
               'on': cfg.get('scripts', 'switchon'),
               'off': cfg.get('scripts', 'switchoff'),
               'status': cfg.get('scripts', 'status')}
    
    # TODO documentare che questo non viene usato internamente
    # può essere usato dagli script, a disposizione del programmatore
    #device = cfg['scripts']['device']
    
    host = cfg.get('socket', 'host')  # TODO decidere come gestire l'ascolto su tutte le interfacce
    port = cfg.getint('socket', 'port')
    
    if (port < 0) or (port > 65535):
        raise ValueError('socket port is outside range 0-65535')

except configparser.NoSectionError as nse:
    ret_code = 16
    logger.critical('incomplete configuration file, missing `%s` section',
                    nse.section)

except configparser.NoOptionError as noe:
    ret_code = 17
    logger.critical('incomplete configuration file, missing option `%s` '
                    'in section `%s`', noe.option, noe.section)

except configparser.Error as cpe:
    ret_code = 18
    logger.critical('unknown error in configuration file: `%s`', cpe)

except ValueError as ve:
    ret_code = 19
    logger.critical('invalid configuration file: {}'.format(ve))

except Exception as e:
    ret_code = 20
    logger.critical('unknown error in configuration file: `{}`'.format(e))

except:
    ret_code = 20
    logger.critical('unknown error in configuration file, no more details')

else:
    ret_code = 0

finally:
    if ret_code == 0:
        logger.debug('main settings read')
    else:
        logger.info('closing daemon with return code {}'.format(ret_code))
        exit(ret_code)

# if the daemon is disabled in configuration file we exit immediatly
if not enabled:
    logger.info('daemon disabled in configuration file, exiting...')
    exit(0)

# re-setting debug level read from configuration file
if debug:
    logger.setLevel(logging.DEBUG)

# initializing base objects
try:
    logger.debug('creating base classes')
    heating = ScriptHeating(scripts['on'], scripts['off'], scripts['status'], debug)
    timetable = TimeTable(tt_file, heating)

except FileNotFoundError as fnfe:
    ret_code = 20
    logger.critical('cannot find timetable file `%s`', tt_file)

except Exception as e:
    ret_code = 21
    logger.critical('unknown error during daemon initialization: %s', e)

except:
    ret_code = 21
    logger.critical('unknown error during daemon initialization, no more details')

else:
    ret_code = 0
    
finally:
    if ret_code != 0:
        logger.info('closing daemon with return code {}'.format(ret_code))
        exit(ret_code)

def shutdown(signum=None, frame=None):
    global enabled
    logger.info('shutdown requested')
    with timetable.lock:
        enabled = False
        timetable.lock.notify()

def reload_timetable(signum=None, frame=None):
    logger.info('timetable reload requested')
    with timetable.lock:
        timetable.reload()
        timetable.lock.notify()

def thermostat_cycle():
    # TODO scrivere documentazione
    logger.info('daemon started')
    
    # starting control socket
    socket = ControlThread(timetable, host, port)
    socket.start()
    
    logger.info('the heating is currently %s', (heating.is_on() and 'ON' or 'OFF'))
    
    while enabled:
        try:
            logger.debug('retriving current temperature')
            t = subprocess.check_output(scripts['tsensor'], shell=True).decode('utf-8').strip()
            logger.debug('current temperature: %s',t)
            
            with timetable.lock:
                if timetable.should_the_heating_be_on(t):
                    if not heating.is_on():
                        heating.switch_on()
                        logger.info('heating switched ON')
                    else:
                        logger.debug('heating already ON')
                else:
                    if heating.is_on():
                        heating.switch_off()
                        logger.info('heating switched OFF')
                    else:
                        logger.debug('heating already OFF')
        
        except subprocess.CalledProcessError as cpe:
            # TODO
            logger.critical(str(cpe))
        
        except JsonValueError as jve:
            # TODO
            logger.critical(str(jve))
        
        except HeatingError as he:
            # TODO
            logger.critical(str(he))
            logger.debug(he.suberror)
        
        except Exception as e:
            # TODO
            logger.critical(str(e))
            # TODO qui ci deve essere uno shutdown()
        
        # TODO forse in foreground serve intercettare KeyboardInterrupt
        
        try:
            with timetable.lock:
                # TODO se c'è stato uno shutdown prima di arrivare qui, si deve
                # uscire senza andare in wait, trovare come fare
                timetable.lock.wait(interval)
        
        except KeyboardInterrupt:
            shutdown()
    
    logger.debug('stopping daemon')
    with timetable.lock:
        socket.stop()
        socket.join(10)
        
        heating.switch_off()
        logger.info('heating switched OFF')
        # TODO gestire eccezioni

    logger.info('daemon stopped')


# main
if args.foreground:
    logger.debug('starting daemon in foreground')
    
    # TODO aggiungere gli altri segnali
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGUSR1, reload_timetable)
    
    thermostat_cycle()

else:
    logger.debug('starting daemon in background')
    
    daemon = DaemonContext()
    daemon.signal_map={signal.SIGTERM: shutdown,
                       signal.SIGUSR1: reload_timetable}  # TODO aggiungere gli altri segnali

    if args.log:
        daemon.files_preserve = [logfile.stream]

    with daemon:
        thermostat_cycle()
