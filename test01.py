#!/usr/bin/env python

# shor test for timetable module
# TODO aggiungere un test per save del file json

import logging
import argparse
import sys

from datetime import datetime
from thermod import config
from thermod.timetable import TimeTable

parser = argparse.ArgumentParser(description='thermod test01')
parser.add_argument('-D','--debug', action='store_true', help='start the daemon in debug mode')
parser.add_argument('-L','--log', action='store', default=None, help='write messages to log file')
parser.add_argument('-J','--json', action='store', default=None, help='load this json file')
args = parser.parse_args()

logger = logging.getLogger('thermod')

if args.debug:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

console = logging.StreamHandler(sys.stdout)
console.setFormatter(logging.Formatter(fmt='%(asctime)s %(name)-8s %(levelname)-8s %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(console)

logger.debug('added console output to logger')

if args.log:
    logfile = logging.FileHandler(args.log, mode='w')
    logfile.setFormatter(logging.Formatter(fmt='%(asctime)s - %(name)-20s - %(levelname)-8s %(message)s',datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(logfile)
    logger.debug('added file output to logger: {}'.format(args.log))


try:
    logger.info('creating TimeTable')
    t = TimeTable(args.json or 'timetable.json')
    
    logger.info('testing heating with 19.38 degree')
    result = t.should_the_heating_be_on(19.38)
    if result:
        logger.info('switching on')
    else:
        logger.info('switching off')
    
    logger.info('testing heating with 21.4 degree')
    result = t.should_the_heating_be_on(21.4)
    if result:
        logger.info('switching on')
    else:
        logger.info('switching off')

    logger.info('updating current time to 30 degrees')
    now = datetime.now()
    day = config.json_days_name_map[now.strftime('%w')]
    hour = config.json_format_hour(now.hour)
    quarter = int(now.minute // 15)
    t.update(int(now.strftime('%w')),hour,quarter,30)
    
    logger.info('testing again the heating with 21.4 degrees')
    result = t.should_the_heating_be_on(21.4)
    if result:
        logger.info('switching on')
    else:
        logger.info('switching off')
    
except Exception as err:
    logger.critical(err)

