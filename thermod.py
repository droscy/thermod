#!/usr/bin/env python3

import os
import sys
import logging
import argparse
import signal
import configparser

from daemon import DaemonContext
from logging.handlers import SysLogHandler
from jsonschema import ValidationError

from thermod import config
from thermod.thermometer import ScriptThermometer, ThermometerError
from thermod.heating import ScriptHeating, HeatingError
from thermod.timetable import TimeTable
from thermod.socket import ControlThread
from thermod.config import JsonValueError, ScriptError

# TODO usare /usr/bin/python3 al posto di env in tutti gli script e script generati dai test
# TODO mettere un SMTPHandler per i log di tipo WARNING e CRITICAL
# TODO verificare il corretto spelling di thermod o Thermod in tutti i sorgenti
# TODO documentare return code
# TODO provare la generazione della documentazione con doxygen

# TODO rivedere i messaggi di log, decidere se usare %-formatting
# oppure https://docs.python.org/3/howto/logging-cookbook.html#use-of-alternative-formatting-styles
# usando StyleAdapter

prog_version = '0.0.0~alpha4'
script_path = os.path.dirname(os.path.realpath(__file__))
main_return_code = config.RET_CODE_OK

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
    # TODO cosa succede se non riesce a scrivere nel log? Solleva PermissionError
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
    cfg = configparser.ConfigParser()
    cfg.read_string('[global] enabled = 0')  # basic settings to immediatly shutdown if config file is missing
    logger.debug('searching main configuration in files {}'.format(config.main_config_files))
    
    _cfg_files_found = cfg.read(config.main_config_files) # TODO in caso di più file quale ha precedenza?
    
    if _cfg_files_found:
        logger.debug('configuration files found: {}'.format(_cfg_files_found))
    else:
        main_return_code = config.RET_CODE_CFG_FILE_MISSING
        logger.critical('no configuration files found in %s', config.main_config_files)

except configparser.MissingSectionHeaderError as mshe:
    main_return_code = config.RET_CODE_CFG_FILE_SYNTAX_ERR
    logger.critical('invalid syntax in configuration file `%s`, '
                    'missing sections', mshe.source)

except configparser.ParsingError as pe:
    main_return_code = config.RET_CODE_CFG_FILE_SYNTAX_ERR
    (_lineno, _line) = pe.errors[0]
    logger.critical('invalid syntax in configuration file `%s` at line %d: %s',
                    pe.source, _lineno, _line)

except configparser.DuplicateSectionError as dse:
    main_return_code = config.RET_CODE_CFG_FILE_INVALID
    logger.critical('duplicate section `%s` in configuration file `%s`',
                    dse.section, dse.source)

except configparser.DuplicateOptionError as doe:
    main_return_code = config.RET_CODE_CFG_FILE_INVALID
    logger.critical('duplicate option `%s` in section `%s` of configuration '
                    'file `%s`', doe.option, doe.section, doe.source)

except configparser.Error as cpe:
    main_return_code = config.RET_CODE_CFG_FILE_UNKNOWN_ERR
    logger.critical('parsing error in configuration file: `%s`', cpe)

except Exception as e:
    main_return_code = config.RET_CODE_CFG_FILE_UNKNOWN_ERR
    logger.critical('unknown error in configuration file: `%s`', e)

except:
    main_return_code = config.RET_CODE_CFG_FILE_UNKNOWN_ERR
    logger.critical('unknown error in configuration file, no more details')

else:
    main_return_code = config.RET_CODE_OK
    logger.debug('main configuration files read')

finally:
    if main_return_code != config.RET_CODE_OK:
        logger.info('closing daemon with return code {}'.format(main_return_code))
        exit(main_return_code)


# parsing main settings
try:
    # TODO finire controllo sui valori presenti nel file di config
    enabled = cfg.getboolean('global', 'enabled')
    debug = cfg.getboolean('global', 'debug') or args.debug
    tt_file = cfg.get('global', 'timetable')
    interval = cfg.getint('global', 'interval')
    
    scripts = {'thermo': cfg.get('scripts', 'thermometer'),
               'on': cfg.get('scripts', 'switchon'),
               'off': cfg.get('scripts', 'switchoff'),
               'status': cfg.get('scripts', 'status')}
    
    # TODO documentare che questo non viene usato internamente
    # può essere usato dagli script, a disposizione del programmatore
    #device = cfg['scripts']['device']
    
    host = cfg.get('socket', 'host')  # TODO decidere come gestire l'ascolto su tutte le interfacce
    port = cfg.getint('socket', 'port')
        
    if (port < 0) or (port > 65535):
        # checking port here because the ControlThread is created after starting
        # the daemon and the resulting log file can be messy
        raise OverflowError('socket port is outside range 0-65535')

except configparser.NoSectionError as nse:
    main_return_code = config.RET_CODE_CFG_FILE_INVALID
    logger.critical('incomplete configuration file, missing `%s` section',
                    nse.section)

except configparser.NoOptionError as noe:
    main_return_code = config.RET_CODE_CFG_FILE_INVALID
    logger.critical('incomplete configuration file, missing option `%s` '
                    'in section `%s`', noe.option, noe.section)

except configparser.Error as cpe:
    main_return_code = config.RET_CODE_CFG_FILE_UNKNOWN_ERR
    logger.critical('unknown error in configuration file: `%s`', cpe)

except ValueError as ve:
    # raised by getboolean() and getint() methods
    main_return_code = config.RET_CODE_CFG_FILE_INVALID
    logger.critical('invalid configuration: `{}`'.format(ve))

except OverflowError as oe:
    main_return_code = config.RET_CODE_CFG_FILE_INVALID
    logger.critical('invalid configuration: `{}`'.format(oe))

except Exception as e:
    main_return_code = config.RET_CODE_CFG_FILE_UNKNOWN_ERR
    logger.critical('unknown error in configuration file: `{}`'.format(e))

except:
    main_return_code = config.RET_CODE_CFG_FILE_UNKNOWN_ERR
    logger.critical('unknown error in configuration file, no more details')

else:
    main_return_code = config.RET_CODE_OK
    logger.debug('main settings read')

finally:
    if main_return_code != config.RET_CODE_OK:
        logger.info('closing daemon with return code {}'.format(main_return_code))
        exit(main_return_code)


# if the daemon is disabled in configuration file we exit immediatly
if not enabled:
    logger.info('daemon disabled in configuration file, exiting...')
    exit(config.RET_CODE_DAEMON_DISABLED)


# setting again the debug level if requested in configuration file
if debug:
    logger.setLevel(logging.DEBUG)


# initializing base objects
try:
    logger.debug('creating base objects')
    
    heating = ScriptHeating(scripts['on'], scripts['off'], scripts['status'], debug)
    thermometer = ScriptThermometer(scripts['thermo'], debug)
    timetable = TimeTable(tt_file, heating, thermometer)

except FileNotFoundError as fnfe:
    main_return_code = config.RET_CODE_TT_NOT_FOUND
    logger.critical('cannot find timetable file `%s`', tt_file)

except PermissionError as pe:
    main_return_code = config.RET_CODE_TT_READ_ERR
    logger.critical('cannot read timetable file `%s`', tt_file)

except OSError as oe:
    main_return_code = config.RET_CODE_TT_OTHER_ERR
    logger.critical('error accessing timetable file `%s`', tt_file)
    logger.critical(str(oe))

except ValueError as ve:
    main_return_code = config.RET_CODE_TT_INVALID_SYNTAX
    logger.critical('timetable file is not in JSON format or has syntax errors')
    logger.critical(str(ve))

except ValidationError as jve:
    main_return_code = config.RET_CODE_TT_INVALID_CONTENT
    logger.critical('timetable file is invalid: %s', jve)

except Exception as e:
    main_return_code = config.RET_CODE_INIT_ERR
    logger.critical('error during daemon initialization: %s', e)

except:
    main_return_code = config.RET_CODE_INIT_ERR
    logger.critical('unknown error during daemon initialization, no more details')

else:
    main_return_code = config.RET_CODE_OK
    logger.debug('base objects created')
    
finally:
    if main_return_code != config.RET_CODE_OK:
        logger.info('closing daemon with return code {}'.format(main_return_code))
        exit(main_return_code)


def shutdown(signum=None, frame=None, exitcode=config.RET_CODE_OK):
    global enabled, main_return_code
    logger.info('shutdown requested')
    with timetable.lock:
        enabled = False
        timetable.lock.notify()
    main_return_code = exitcode  # setting the global return code


def reload_timetable(signum=None, frame=None):
    logger.info('timetable reload requested')
    with timetable.lock:
        # TODO mettere tutte le eccezioni del caso
        timetable.reload()
        timetable.lock.notify()


def thermostat_cycle():
    # TODO scrivere documentazione
    logger.info('daemon started')
    
    try:
        # starting control socket
        socket = ControlThread(timetable, host, port)
        socket.start()
    
    except OSError as oe:
        # TODO OSError: [Errno 98] Address already in use
        pass
    
    except Exception as e:
        # TODO
        pass
    
    else:
        logger.info('the heating is currently %s', (heating.is_on() and 'ON' or 'OFF'))
        
        while enabled:
            try:
                with timetable.lock:
                    try:
                        # TODO sarebbe comodo mostrare nel log anche la temperatura
                        # corrente e quella target ogni volta che cambia lo stato
                        # del riscaldamento
                        if timetable.should_the_heating_be_on():
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
                    
                    except ValidationError as ve:
                        # The internal settings must be valid otherwise an error
                        # should have been already catched in other sections of
                        # the daemon, even if new settings are set from
                        # socket connection. So we print a critical error and
                        # we close the daemon.
                        logger.critical(ve)
                        shutdown(exitcode=config.RET_CODE_RUN_INVALID_STATE)
                    
                    except JsonValueError as jve:
                        # A strange value has been set somewhere and the daemon
                        # didn't catch the appropriate exception. We print a
                        # critical message and we close the daemon.
                        logger.critical(jve)
                        shutdown(exitcode=config.RET_CODE_RUN_INVALID_VALUE)
                    
                    except ScriptError as se:
                        # One of the external scripts reported an error, we
                        # print it as a severe error but we leave the daemon
                        # running even if probably it is not fully functional.
                        logger.error('the script `%s` reported the following '
                                     'error: %s', se.script, se)
                    
                    except ThermometerError as te:
                        logger.error('error from thermometer: %s', te)
                        logger.debug(te.suberror)
                    
                    except HeatingError as he:
                        logger.error('error from heating: %s', he)
                        logger.debug(he.suberror)
                    
                    except Exception as e:
                        # An unknown error occurred somewhere
                        logger.exception('unknown error occurred: %s', e)
                        shutdown(exitcode=config.RET_CODE_RUN_OTHER_ERR)
                    
                    # A shutdown may have been requested before reaching
                    # this point and in such situation we don't have to
                    # wait for a notify, simply go on and exit the cycle.
                    if enabled:
                        timetable.lock.wait(interval)
            
            except KeyboardInterrupt:
                shutdown(exitcode=config.RET_CODE_KEYB_INTERRUPT)
    
    finally:    
        logger.debug('stopping daemon')
        
        try:
            with timetable.lock:
                socket.stop()
                socket.join(10)
        
        except NameError:
            # The socket doesn't exist because and error has occurred during
            # its creation, the error has already been logged so we simply
            # ignore this exception. Or, maybe, a KeyboardInterrupt has been
            # raised just before the creation of the socket and the socket
            # still doesn't exist.
            pass
        
        except RuntimeError:
            # Probably this exception is raised by the join() method because
            # an error has occurred during socket starting. The error has
            # already been logged and we simply ignore this exception.
            pass
        
        except Exception as e:
            logger.exception('unexpected error stopping control socket: %s', e)
            shutdown(exitcode=config.RET_CODE_RUN_OTHER_ERR)
        
        try:
            if heating.is_on():
                heating.switch_off()
                logger.info('heating switched OFF')
        
        # No call to shutdown() in the following exceptions because the exit
        # code must be the same set somewhere else, here we simply report the
        # error during shutdown.
        except Exception as e:
            logger.warning('cannot switch off the heating')
            logger.error(e)
        
        except:
            logger.error('unknown error in switching off the heating during '
                         'daemon shutdown')
        
        # TODO gestire eccezioni

    logger.info('daemon stopped')


# main
if args.foreground:
    logger.debug('starting daemon in foreground')
    
    # TODO aggiungere gli altri segnali e usare SIGHUP
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGUSR1, reload_timetable)
    
    thermostat_cycle()

else:
    logger.debug('starting daemon in background')
    
    daemon = DaemonContext()
    daemon.signal_map={signal.SIGTERM: shutdown,
                       signal.SIGUSR1: reload_timetable}  # TODO aggiungere gli altri segnali e usare SIGHUP

    if args.log:
        daemon.files_preserve = [logfile.stream]

    with daemon:
        thermostat_cycle()

exit(main_return_code)
