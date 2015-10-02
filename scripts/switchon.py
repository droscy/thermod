#!/usr/bin/env python3
# encoding: utf-8
"""
Switch on the heating using a serial TTL relay.

@author:     Simone Rossetto
@copyright:  2015 Simone Rossetto
@license:    GNU General Public License v3
@contact:    simros85@gmail.com
"""

#import os
import sys
import json
import logging

from argparse import ArgumentParser
from configparser import ConfigParser
from serial import Serial, SerialException, EIGHTBITS, STOPBITS_ONE, PARITY_NONE
from thermod import config


__version__ = '0.0.1'
__date__ = '2015-10-02'
__updated__ = '2015-10-02'


relay_msg_bytes = 8
relay_cmd_close = b'\x55\x56\x00\x00\x00\x00\x02\xAD'
relay_rsp_close = b'\x33\x3C\x00\x00\x00\x00\x02\x71'


def main(argv=None):
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)
    
    #prog_name = os.path.basename(sys.argv[0])
    prog_version = 'v%s' % __version__
    prog_build_date = str(__updated__)
    prog_version_msg = '%%(prog)s %s (%s)' % (prog_version, prog_build_date)
    prog_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    
    result = None
    device = None
    error = None
    
    # TODO aggiungere un example usage nell'epilog di ArgumentParser
    parser = ArgumentParser(description=prog_shortdesc)
    parser.add_argument('--version', action='version', version=prog_version_msg)
    parser.add_argument('--debug', action='store_true', help='execute in debug mode')
    parser.add_argument('-d','--device', action='store', default=None, help='use custom serial device')
    parser.add_argument('-j','--json', action='store_true', help='output messages in json format')
    args = parser.parse_args()
    
    logger = logging.getLogger('thermod.switch.on')

    if args.debug:
        logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(logging.Formatter(fmt=config.logger_fmt, datefmt=config.logger_datefmt))
    logger.addHandler(console)
    
    logger.debug('program started')
    
    logger.debug('reading main configuration from files {}'.format(config.main_config_files))
    cfg = ConfigParser()
    _cfg_files_found = cfg.read(config.main_config_files)
    logger.debug('configuration files found: {}'.format(_cfg_files_found))

    # device provided by command line arguments has the precedence
    if ((cfg.has_section('scripts') and cfg.has_option('scripts', 'device'))
            or args.device):
        device = (args.device or cfg['scripts']['device'])
        logger.debug('device set to: {}'.format(device))
    
    
    try:
        logger.debug('initializing serial port')
        
        # Baud rate 9600kbps, 8 data bits, one stop bit, no parity
        #
        # Control commands
        #     Bytes Number    1    2    3    4    5    6    7    8
        #                     Head      Reserved bytes      Cmd  Checksum
        #     Reading status  0x5556    0x00000000          00   0xAB
        #     Relay open      0x5556    0x00000000          01   0xAC
        #     Relay close     0x5556    0x00000000          02   0xAD
        #     Relay toggle    0x5556    0x00000000          03   0xAE
        #     Relay momentary 0x5556    0x00000000          04   0xAF
        #
        # Return value
        #     Bytes Number    1    2    3    4    5    6    7    8
        #                     Head      Reserved bytes      Cmd  Checksum
        #     Relay open      0x333C    0x00000000          01   0x70
        #     Relay closed    0x333C    0x00000000          02   0x71
        serial = Serial(port=device,
                        baudrate=9600,
                        timeout=5,  # read timeout in seconds
                        bytesize=EIGHTBITS,
                        stopbits=STOPBITS_ONE,
                        parity=PARITY_NONE)
    
        with serial:
            logger.debug('sending command to close the relay')
            written = serial.write(relay_cmd_close)
        
            if (written != relay_msg_bytes):
                logger.debug('number of bytes written ({}) is less than number '
                             'of bytes in close command ({})'
                             .format(written, relay_msg_bytes))
                raise SerialException('number of bytes written is less than '
                                      'number of bytes in close command')
            
            logger.debug('retriving status message from relay')
            status = serial.read(relay_msg_bytes)
            
            if (status != relay_rsp_close):
                logger.debug('returned message from relay reports a '
                             'non-closed status: {}'.format(status))
                raise SerialException('returned message from relay reports a '
                                      'non-closed status')
        
        logger.debug('the heating has been switched on')
        result = 0
    
    except SerialException as se:
        error = str(se)
        
        if not args.json or args.debug:
            logger.critical(error)
        
        result = 1
    
    if args.json:
        logger.debug('printing result as json encoded string')
        print(json.dumps({'success': not result, 'error': error}))
    
    logger.debug('exiting with return code = {}'.format(result))
    return result


if __name__ == "__main__":
    sys.exit(main())
