#!/usr/bin/env python3

import os
import sys
import logging
import argparse
import signal
import subprocess

from daemon import DaemonContext
from configparser import ConfigParser
from logging.handlers import SysLogHandler
from thermod import config
from thermod.heating import ScriptHeating, HeatingError
from thermod.timetable import TimeTable
from thermod.socket import ControlThread
from thermod.config import JsonValueError

# TODO mettere un SMTPHandler per i log di tipo WARNING e CRITICAL
# TODO usare impostazione "enable" del file di config

prog_version = '0.0.0~alpha1'
script_path = os.path.dirname(os.path.realpath(__file__))
config_files = [os.path.abspath(os.path.join(script_path,'thermod.conf'))]
config_files.extend(list(config.main_config_files))

# parsing input arguments
parser = argparse.ArgumentParser(description='thermod daemon')
parser.add_argument('--version', action='version', version='%(prog)s {}'.format(prog_version))
parser.add_argument('-D','--debug', action='store_true', help='start the daemon in debug mode')
parser.add_argument('-F','--foreground', action='store_true', help='start the daemon in foreground')
parser.add_argument('-L','--log', action='store', default=None, help='write messages to log file')
args = parser.parse_args()

# setting up logging system
logger = logging.getLogger('thermod')
logger.setLevel(logging.INFO)

if args.debug:
    logger.setLevel(logging.DEBUG)

if args.foreground:
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(fmt=config.logger_fmt_msg,
                                           datefmt=config.logger_fmt_time,
                                           style=config.logger_fmt_style))
    logger.addHandler(console)
else:
    syslog = SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_DAEMON)
    syslog.setFormatter(logging.Formatter(fmt=config.logger_fmt_msg_syslog,
                                          style=config.logger_fmt_style))
    logger.addHandler(syslog)

if args.log:
    logfile = logging.FileHandler(args.log, mode='w')  # TODO forse mode='a'
    logfile.setFormatter(logging.Formatter(fmt=config.logger_fmt_msg,
                                           datefmt=config.logger_fmt_datetime,
                                           style=config.logger_fmt_style))
    logger.addHandler(logfile)

# reading main config file
cfg = ConfigParser()
cfg.read_string('[global] enabled = 0')
logger.debug('reading config files')
cfg.read(config_files) # TODO in caso di più file quale ha precedenza?
scripts = cfg['scripts']
# TODO inserire un controllo sui valori presenti nel file di config

if int(cfg['global']['debug']) == 1:
    logger.setLevel(logging.DEBUG)

# initializing base objects
logger.debug('creating base classes')
heating = ScriptHeating(scripts['switchon'], scripts['switchoff'], scripts['status'])
timetable = TimeTable(cfg['global']['timetable'], heating)
socket = ControlThread(timetable)
running = True

# TODO come si ricaricano le impostazioni? con funzione di reload() e variabili global?

def shutdown(a=None, b=None):
    global running, timetable, logger
    logger.info('shutdown requested')
    with timetable.lock:
        running = False
        timetable.lock.notify()

daemon = DaemonContext()
daemon.signal_map={signal.SIGTERM: shutdown,
                   signal.SIGUSR1: timetable.reload}

if args.log:
    daemon.files_preserve = [logfile.stream]

# TODO questo segnale va intercettato solo per forground
signal.signal(signal.SIGTERM, shutdown)

logger.debug('starting daemon')
# TODO fare sì che l'opzione -F non faccia partire il demone
#with daemon:
if True:
    logger.info('daemon started')
    
    # TODO forse il socket va fatto avvia dentro il demone?
    socket.start()
    
    while running:
        try:
            logger.debug('retriving current temperature')
            t = subprocess.check_output(scripts['sensor'], shell=True).decode('utf-8').strip()
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
                timetable.lock.wait(30)
        
        except KeyboardInterrupt:
            shutdown()
    
    logger.debug('stopping daemon')
    with timetable.lock:
        socket.stop()
        socket.join(10)
        
        logger.info('switch off the heating')
        heating.switch_off()
        # TODO gestire eccezioni

    logger.info('daemon stopped')
