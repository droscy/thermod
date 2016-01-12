#!/usr/bin/env python3

import os
import sys
import logging
import logging.handlers
import argparse
import signal
import subprocess

from daemon import DaemonContext
from configparser import ConfigParser
from thermod import config
from thermod.heating import ScriptHeating, HeatingError
from thermod.timetable import TimeTable
from thermod.socket import ControlThread
from thermod.config import JsonValueError

# TODO mettere un SMTPHandler per i log di tipo WARNING e CRITICAL

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

# starting base logging system
logger = logging.getLogger('thermod')
logger.setLevel(logging.INFO)

if args.debug:
    logger.setLevel(logging.DEBUG)

if args.foreground:
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(fmt=config.logger_fmt_msg, datefmt=config.logger_fmt_date))
    logger.addHandler(console)
else:
    # TODO syslog non funziona
    syslog = logging.handlers.SysLogHandler()
    #syslog.addFormatter(logging.Formatter(fmt=config.logger_fmt_msg_syslog))
    logger.addHandler(syslog)

if args.log:
    logfile = logging.FileHandler(args.log, mode='w')
    logfile.setFormatter(logging.Formatter(fmt=config.logger_fmt_msg,datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(logfile)

# reading main config file
cfg = ConfigParser()
cfg.read_string('[global] enabled = 0')
logger.debug('reading config files')
cfg.read(config_files) # TODO in caso di più file quale ha precedenza?
scripts = cfg['scripts']
# TODO inserire un controllo sui valori presenti nel file di config

# initializing base objects
logger.debug('creating base classes')
heating = ScriptHeating(scripts['switchon'], scripts['switchoff'], scripts['status'])
timetable = TimeTable(cfg['global']['timetable'], heating)
socket = ControlThread(timetable)
running = True

def shutdown():
    global running, timetable
    with timetable.lock:
        running = False
        timetable.lock.notify()

daemon = DaemonContext()
daemon.signal_map={signal.SIGTERM: shutdown,
                   signal.SIGUSR1: timetable.reload}

socket.start()

logger.debug('starting daemon')
# TODO il demone parte ma non scrive log
# TODO fare sì che l'opzione -F non faccia partire il demone
#with daemon:
if True:
    logger.info('daemon started')
    while running:
        try:
            t = subprocess.check_output(scripts['sensor'], shell=True)
            
            with timetable.lock:
                if timetable.should_the_heating_be_on(t):
                    # TODO spostare qui la chiamata a is_on() e rimuoverla dagli switch
                    heating.switch_on()
                else:
                    heating.switch_off()
        
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
        
        # TODO forse in foreground serve intercettare KeyboardInterrupt
        
        with timetable.lock:
            timetable.lock.wait(30)
    
    logger.debug('stopping daemon')
    with timetable.lock:
        socket.stop()
        socket.join(10)
        heating.switch_off()
        # TODO gestire eccezioni

    logger.info('daemon stopped')
