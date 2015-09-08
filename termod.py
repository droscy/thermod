#!/usr/bin/env python

import argparse
import logging
import platform
import sys
import time

# TODO il package time è stato importato per gli sleep, va tolto quando si tolgono gli sleep
# TODO thread che apre il socket
# TODO thread che monitora la temperatura
# TODO doppio fork per il demone
# TODO gestione dei segnali per stoppare il demone

prog_version = '0.0.0~alpha1'

parser = argparse.ArgumentParser(description='termod daemon')
parser.add_argument('--version', action='version', version='%(prog)s {}'.format(prog_version))
parser.add_argument('-D','--debug', action='store_true', help='start the daemon in debug mode')
parser.add_argument('-F','--foreground', action='store_true', help='start the daemon in foreground')
parser.add_argument('-L','--log', action='store', default=None, help='write message to log file')

args = parser.parse_args()

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

logger.debug('Starting Daemon...')

logger.info('Daemon started')

logger.info('Starting first cycle')
for i in range(10):
    logger.debug('counter = {}'.format(i))
    time.sleep(1)
logger.info('Daemon stopped')
