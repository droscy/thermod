#!/bin/bash
# -*- coding: utf-8 -*-
# Wrapper for pcsensor https://github.com/peterfarsinsen/pcsensor.git
# This script extracts temperature from CSV and prints a JSON string as
# required by ScriptThermometer class of Thermod daemon.
# 
# @author     Simone Rossetto
# @copyright  2016 Simone Rossetto
# @license    GNU General Public License v3
# @contact    simros85@gmail.com
# @version    1.0
#

# init variables
DEBUG=0
LANG=POSIX
PCSENSOR='/usr/local/bin/pcsensor -c -s'
PYMODULE='thermod.temperature'

# check required programs
REQUIRED_PROGRAMS=( logger cut printf )
for prog in ${REQUIRED_PROGRAMS[@]}; do
  if ! hash "$prog" 1>/dev/null 2>/dev/null; then
    echo -n "{\"error\": \"required program ${prog} not found\", \"temperature\": null}"
    exit 255
  fi
done

# parsing arguments for debug option
while :; do
  case $1 in
    -d|--debug) DEBUG=1 ;;
    *) break
  esac
  shift
done

# logging function
log()
{
  if [ "${1:-debug}" != 'debug' ]; then
    logger -t "${PYMODULE}" -i -p user.$1 -- "${1^^} ${2:-no message reported}"
  elif [ ${DEBUG} -eq 1 ]; then
    logger -t "${PYMODULE}" -i -p user.debug -- "DEBUG ${2:-no message reported}"
  fi
}

# main
log debug "querying thermometer using program '${PCSENSOR}'"
CSV=$(${PCSENSOR})

RET=$?
if [ ${RET} -ne 0 ]; then
  log debug "pcsensor exited with error code ${RET} and message '${CSV}'"
  printf '{"error": "%s", "temperature": null}' "${CSV}"
  exit ${RET}
fi

log debug "extracting temperature from CSV output '${CSV}'"
TEMPERATURE=$(echo -n "${CSV}" | cut -d \; -f 4)

RET=$?
if [ ${RET} -ne 0 ]; then
  log debug "cannot extract temperature from CSV: '${TEMPERATURE}'"
  printf '{"error": "%s", "temperature": null}' "${TEMPERATURE}"
  exit ${RET}
fi

log debug "converting temperature '${TEMPERATURE}' to number"
JSON=$(printf '{"temperature": %.2f, "error": null}' "${TEMPERATURE}")

RET=$?
if [ ${RET} -ne 0 ]; then
  err="cannot convert temperature '${TEMPERATURE}' to number"
  log debug "${err}"
  printf '{"error": "%s", "temperature": null}' "${err}"
  exit ${RET}
fi

log debug "$(printf 'current temperature is %.2f' "${TEMPERATURE}")"
echo -n "${JSON}"
exit 0

# vim: fileencoding=utf-8