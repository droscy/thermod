#!/usr/bin/env python

import argparse
import logging
import os
import sys
import time

from configparser import ConfigParser
from threading import Thread, Lock, Event

# TODO il package time è stato importato per gli sleep, va tolto quando si tolgono gli sleep
# TODO thread che apre il socket
# TODO doppio fork per il demone
# TODO gestione dei segnali per stoppare il demone

# TODO timetable in json
#  - status: <auto|t0|tmin|tmax|off|on>
#  - t0, tmin, tmax: la temperatura in float

# TODO mettere un SMTPHandler per i log di tipo WARNING e CRITICAL

prog_version = '0.0.0~alpha1'
script_path = os.path.dirname(os.path.realpath(__file__))
config_files = [os.path.abspath(os.path.join(script_path,'termod.conf')),
                os.path.expanduser('~/.termod.conf'),
                '/etc/termod/termod.conf']

# class TemperatureCheckingThread(Thread):
#     '''This thread checks the temperature and switch on/off the heating according to timetable'''
#     
#     def __init__(self):
#         self.check = Event()
#         Thread.__init__(self)
#     
#     def run(self):
#         while True:
#             pass

# parsing input arguments
parser = argparse.ArgumentParser(description='termod daemon')
parser.add_argument('--version', action='version', version='%(prog)s {}'.format(prog_version))
parser.add_argument('-D','--debug', action='store_true', help='start the daemon in debug mode')
parser.add_argument('-F','--foreground', action='store_true', help='start the daemon in foreground')
parser.add_argument('-L','--log', action='store', default=None, help='write messages to log file')
args = parser.parse_args()

# starting base logging system
logger = logging.getLogger('termod')
logger.setLevel(logging.INFO)

if args.debug:
    logger.setLevel(logging.DEBUG)

if args.foreground:
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(fmt='%(asctime)s %(name)-8s %(levelname)-8s %(message)s', datefmt='%H:%M:%S'))
    logger.addHandler(console)
else:
    syslog = logging.SysLogHandler()
    syslog.addFormatter(logging.Formatter(fmt='%(name)-8s: %(levelname)-8s %(message)s'))
    logger.addHandler(syslog)

if args.log:
    logfile = logging.FileHandler(args.log, mode='w')
    logfile.setFormatter(logging.Formatter(fmt='%(asctime)s - %(name)s - %(levelname)-8s %(message)s',datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(logfile)

cfg = ConfigParser()
cfg.read_string('[global] enabled = 0')

# TODO serve una classe o un metodo o unmoduelo con il timetable per sapere se accendere
# o spegnere penso che sia più corretto spostare tutta la logica sulla classe, così dai
# vari thread ci si può interfacciare direttamente all'oggetto istanziato

# main
if __name__ == "__main__":
    logger.debug('Reading config files...')
    cfg.read(config_files) # TODO in caso di più file quale ha precedenza?

    logger.debug('Starting socket thread...')
    # TODO thread da scrivere
    logger.debug('Socket thread started')

    

    logger.info('Daemon started')

    logger.info('Starting first cycle')
    for i in range(10):
        logger.debug('counter = {}'.format(i))
        time.sleep(1)
    logger.info('Daemon stopped')
